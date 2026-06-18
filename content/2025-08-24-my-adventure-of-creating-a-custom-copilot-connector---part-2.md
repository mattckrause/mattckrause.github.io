---
title: My Adventure in Building a Custom Copilot Connector - Part 2
description: Second installment of the blog series where I share the process I followed while learning to build a custom Copilot connector. This time in Python, with a richer schema, hosted in Azure.
date: 2026-06-18 11:40
status: published
tags: Copilot connectors, custom connector, Microsoft Copilot, Microsoft Graph, Python, Azure
keywords: Copilot Connector, Python, Graph SDK, Azure App Service
category: Tech Blog
cover: images/GCAdventure.png
---

***

In [Part 1]({filename}/2025-04-05-building-a-custom-graph-connector.md), I walked through the basics of building a Copilot connector using PowerShell — creating an external connection, registering a schema, and writing some simple items. It was a great learning exercise, but it was also very much a proof of concept. The schema was minimal (a single `CompanyName` property), the data was a static CSV file, and there was no real infrastructure behind it.

In this (way past due) post, I'm taking it further. The goal this time is to build something closer to what you'd actually deploy in the real world:

- A **richer schema** designed to make Copilot responses actually useful
- A **Python-based connector** using the Microsoft Graph SDK
- An **external API** as the data source (instead of a static file)
- A look at how to **enable the connector for Copilot** consumption

I'll be honest — the jump from PowerShell scripts to a Python application was a bigger leap than I expected. But if you're comfortable with the concepts from Part 1, you'll be fine. Let's get into it.

***

## Designing a Better Schema

In Part 1, my schema was about as simple as it gets — one property called `CompanyName` marked as searchable and retrievable. It worked, but Copilot couldn't do much with it beyond "hey, I found this thing."

For Part 2, I wanted a schema that would give Copilot enough context to actually answer questions meaningfully. I landed on a schema with four properties:

| Property | Type | Searchable | Retrievable | Label |
|----------|------|-----------|-------------|-------|
| Name | String | ✅ | ✅ | Title |
| Description | String | ✅ | ✅ | — |
| FunFact | String | ❌ | ✅ | — |
| url | String | ❌ | ✅ | Url |

A few key design decisions here:

**Labels matter.** Setting `Name` as the `Title` label tells Copilot "this is the thing's name — use it as the heading." Setting `url` as the `Url` label means Copilot knows where to link for more info. These labels directly impact how results render in Copilot's responses.

**Not everything needs to be searchable.** The `FunFact` property is retrievable but not searchable. That means Copilot can *include* it in responses, but users won't find items by searching for fun facts. This keeps the search index focused on the stuff people are actually looking for.

**Queryable vs. Searchable.** Both `Name` and `Description` are set to `is_queryable=True` as well, which means they support KQL filter queries in addition to full-text search. This matters if you want to build search verticals or filtered views later.

Here's what the schema definition looks like in Python using the Graph SDK:

```python
schema = Schema(
    base_type="microsoft.graph.externalItem",
    properties=[
        Property_(
            name="Name",
            type=PropertyType.String,
            is_queryable=True,
            is_searchable=True,
            is_retrievable=True,
            labels=[Label.Title]
        ),
        Property_(
            name="Description",
            type=PropertyType.String,
            is_queryable=True,
            is_searchable=True,
            is_retrievable=True
        ),
        Property_(
            name="FunFact",
            type=PropertyType.String,
            is_retrievable=True
        ),
        Property_(
            name="url",
            type=PropertyType.String,
            is_retrievable=True,
            labels=[Label.Url]
        )
    ]
)
```

**Remember from Part 1: schema creation takes 5-15 minutes. Don't panic if it doesn't appear immediately.** The middleware I'll show later handles polling for you.

***

## Moving to Python — The Architecture

For Part 1, I used separate PowerShell scripts for each step. That's fine for learning, but not great for anything resembling a real application. For Part 2, I restructured everything into a Python project with clear separation of concerns:

```
PYGraphConnector/
├── main.py               # Orchestrator — runs the connector pipeline
├── graph_client.py       # Creates an authenticated Graph client
├── graph_config.py       # Connection, schema, and item creation logic
├── graph_middleware.py   # Custom middleware for async operation polling
├── external_service.py   # Fetches data from the external API
└── requirements.txt      # Dependencies
```

Now, I should probably admit something here: structuring this as a "real" Python project took me longer than actually writing the Graph API calls. I spent an embarrassing amount of time debugging import paths and async patterns. If you're coming from PowerShell like I was, just know that the hardest part isn't the Graph SDK — it's getting comfortable with Python's way of doing things. Once you get past that, it clicks.

The idea is simple: `main.py` coordinates the flow, `graph_client.py` handles authentication, `graph_config.py` does the Graph API work, `external_service.py` fetches the source data, and `graph_middleware.py` handles the quirk of long-running operations.

### Authentication with the Graph SDK

In Part 1, I used `Connect-MgGraph` with either a certificate or client secret. The Python equivalent uses `azure-identity` and the Microsoft Graph SDK for Python:

```python
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

credential = ClientSecretCredential(
    os.environ.get("_TENANTID"),
    os.environ.get("_APPID"),
    os.environ.get("_CLIENTKEY")
)

graph_client = GraphServiceClient(
    credential,
    scopes=['https://graph.microsoft.com/.default']
)
```

Same concept as Part 1 — Entra app registration, client secret (or certificate), and the `ExternalConnection.ReadWrite.OwnedBy` + `ExternalItem.ReadWrite.OwnedBy` permissions. The only difference is the syntax.

I'm using environment variables through `python-dotenv` to keep credentials out of the code, same pattern as the `.env` file approach from Part 1.

### The Custom Middleware — Handling Long-Running Operations

This is the piece that has no real equivalent in the PowerShell approach. When you create a schema, the Graph API returns a `202 Accepted` with a `Location` header pointing to an operation status URL. You need to poll that URL until the operation completes. In PowerShell, I just waited manually. In Python, I built custom middleware that handles it automatically:

```python
class GraphMiddleware(BaseMiddleware):
    def __init__(self, delayMs: int) -> None:
        super().__init__()
        self.delayMs = delayMs

    async def send(self, request, transport):
        response = await super().send(request, transport)
        location = response.headers.get("Location")

        if location and "/operations/" in location:
            # Schema creation in progress — poll until complete
            time.sleep(self.delayMs / 1000)
            new_request = self.new_request("GET", location, request)
            return await self.send(new_request, transport)

        return response
```

This middleware intercepts responses that contain an operation URL, waits, and then polls the operation endpoint until it either succeeds or fails. It's inserted at the front of the middleware chain when creating the Graph client, so all requests go through it transparently.

Was this strictly necessary? No — I could have just polled manually in the calling code. But it made the connector logic much cleaner. `create_schema()` just calls the API and returns when it's done, without needing to know about polling. I'll also admit this was the part that took me the longest to get right. The Graph SDK's middleware pipeline isn't exactly well-documented for Python, and I spent a solid afternoon staring at httpx internals and sample code before it clicked.

***

## Fetching External Data

In Part 1, I used a static CSV of fictional companies. This time, I'm pulling from an actual external API — an Azure Function that serves a JSON list of objects with names, descriptions, fun facts, and Wikipedia links:

```python
import httpx
import os

async def extract_objects():
    url = os.environ.get("EXTERNAL_API_URL")
    async with httpx.AsyncClient() as client:
        object_response = await client.get(url)
    return object_response.json()
```

The implementation is straightforward — an async HTTP GET that returns JSON. I'm storing the API URL in an environment variable to keep it out of the code (same pattern as the auth credentials). Your own connector would connect to whatever external system you're ingesting from — a CRM, a knowledge base, an internal wiki, a ticketing system — anything with an API.

**A note on testing:** You don't need a real external API to develop your connector. Tools like [Microsoft Dev Proxy](https://learn.microsoft.com/microsoft-cloud/dev/dev-proxy/overview) or [Mockoon](https://mockoon.com/) let you spin up mock APIs locally that return whatever JSON structure you need. I used Dev Proxy during development (more on that below) and it saved me from needing my external service running every time I wanted to test the connector logic.

The important thing is the **mapping step** — taking whatever format your external data is in and mapping it to the schema properties you defined:

```python
object_body = ExternalItem(
    id=obj["ID"],
    properties=Properties(
        additional_data={
            "Name": obj["Name"],
            "Description": obj["Description"],
            "FunFact": obj["FunFact"],
            "URL": obj["WikipediaLink"]
        }
    ),
    acl=[
        Acl(
            type=AclType.Everyone,
            value="everyone",
            access_type=AccessType.Grant
        )
    ]
)
```

Each item gets a unique ID, the properties mapped from the source data, and an ACL. For this example, I'm granting access to everyone — in a real deployment, you'd want to match the ACLs to your actual permission model.

***

## Running the Connector

The orchestrator in `main.py` ties it all together:

```python
import asyncio
from graph_config import create_external_connection, create_schema, write_objects
from external_service import extract_objects

id = 'MKObjectSearch02'
name = 'Random Object Search'
description = 'Random object search. Providing object description, a fun fact, and a Wikipedia link.'

async def main() -> None:
    await create_external_connection(id, name, description)
    await create_schema(id)
    await write_objects(id, await extract_objects())

if __name__ == "__main__":
    asyncio.run(main())
```

Run it, and it:

1. Creates the external connection in your tenant
2. Registers the schema (and waits for it to provision via the middleware)
3. Fetches data from the external API
4. Writes each item into the connection

It's sequential and simple. For a production connector you'd want error handling, retry logic, incremental updates, and probably a scheduler — but for a learning exercise and POC, this gets the job done.

***

## Testing Locally with Dev Proxy

One thing I found really helpful during development was [Dev Proxy](https://learn.microsoft.com/microsoft-cloud/dev/dev-proxy/overview) — a tool from Microsoft that I used to mock my external data source API locally. Instead of needing my Azure Function running every time I wanted to test the connector code, I could simulate the external API responses without any external dependencies.

The setup is a simple JSON config that tells Dev Proxy to intercept requests to a specific URL and return mock data:

```json
{
    "plugins": [{
        "name": "CrudApiPlugin",
        "enabled": true,
        "pluginPath": "~appFolder/plugins/dev-proxy-plugins.dll",
        "configSection": "objectsApi",
        "urlsToWatch": ["https://mkdemoapi.com/*"]
    }],
    "objectsApi": {
        "apiFile": ".apimock/objects-api.json"
    }
}
```

This let me iterate on the connector logic — the schema mapping, the item writing, the error handling — without needing my actual external service up and running. When I was happy with the code, I'd swap back to the real API URL and run it for real.

***

## Enabling the Connector for Copilot

So you've got data flowing into your tenant through a Copilot connector. Now what? This is the part I was most excited about, and honestly, it's also where I had to do the most reading because the docs are spread across a few different places.

Here's what I figured out:

### The Semantic Index Does the Heavy Lifting

Once your items are written to the external connection, the Microsoft 365 semantic index picks them up and processes them. You don't have to do anything special — it just happens. But it's not instant. Depending on how much data you've pushed, it can take anywhere from a few minutes to several hours for new items to become searchable. I definitely refreshed the search results page more times than I'd like to admit waiting for my items to show up.

### Search Verticals — A Nice Bonus

While I was waiting for the semantic index to do its thing, I set up a custom search vertical in the Microsoft 365 admin center. This gives users a dedicated tab in Microsoft Search specifically for your connector data. It's not required, but it's a nice way to make your external content more discoverable even outside of Copilot.

<!-- Add screenshot or link to admin center docs for creating search verticals -->

### Getting Copilot to Actually Use Your Data

Here's the key piece — and the part I was most curious about. Copilot in Microsoft 365 can be grounded on connector data through **declarative agents** or by enabling the connector as a knowledge source through Copilot Studio custom agents. When a user asks Copilot a question that matches content in your connector, the semantic index will include those results in its response — citing the source via the `Url` label you defined in the schema.

The first time I asked Copilot about one of my test objects and it came back with the description, the fun fact, AND a link to the Wikipedia page — all from my connector data — I'll admit I got a little giddy. That's the moment where all the schema work and API plumbing pays off.

### What I Learned About Making Connector Data Useful for Copilot

After going through this whole process, a few things became clear about what makes connector data actually work well with Copilot:

- **Rich descriptions beat lots of properties.** Copilot works best with natural language content. A single well-written `Description` field honestly does more than ten sparse metadata fields.
- **Labels drive the UX.** `Title`, `Url`, `IconUrl`, `LastModifiedDateTime` — these labels tell Copilot and Search how to present your data. Don't skip them.
- **ACLs determine who sees what.** I set everything to "everyone" for this example because it's a test environment. In production, you'd map to Entra ID groups or individual users. Get this wrong and either nobody sees your data or everybody sees data they shouldn't.

***

## What's Different from Part 1

For those keeping score, here's what changed between the PowerShell POC and this Python version:

| Aspect | Part 1 (PowerShell) | Part 2 (Python) |
|--------|---------------------|-----------------|
| Schema | 1 property (CompanyName) | 4 properties with labels |
| Data source | Static CSV | External API |
| Auth | Interactive Graph SDK | Client credentials flow |
| Architecture | Separate scripts | Modular Python app |
| Async handling | Manual wait | Custom middleware |
| Testing | Hard coded .CSV | Real API |

***

## Conclusion

Building this Python connector was a solid next step from the PowerShell proof of concept. The code is on [my GitHub](https://github.com/mattckrause/PYGraphConnector) if you want to poke around, fork it, or use it as a starting point for your own connector.

The big takeaway for me was that the jump from "I can make API calls" to "I have a real application" isn't as huge as it seems. The Graph SDK for Python handles most of the heavy lifting — authentication, request building, serialization. The custom middleware for async operations was the trickiest part, and even that is only about 50 lines of code.

If you're thinking about building your own Copilot connector, here's my advice:

1. **Start with Part 1's approach** — use PowerShell to understand the APIs and concepts
2. **Then move to Python (or C#)** — build something with structure and separation of concerns
3. **Design your schema carefully** — think about what Copilot needs to give good answers, not just what's easy to ingest
4. **Use Dev Proxy for testing** — you'll thank yourself when you're not waiting 15 minutes per iteration

Next up, I'd like to explore hosting this as a proper Azure App Service with scheduled refreshes — but that's a post for another day. Stay tuned.
