---
title: My Adventure in Building a Custom Graph Connector - Part 1
description: The process I went through in building a custom Graph connector.
date: 2025-04-05T14:11:50.658Z
preview: /content/images/GCAdventure.png
tags:
    - Copilot
    - Custom Graph Connector
categories:
    - Blog
---

## Intro

Microsoft Copilot is a pretty amazing piece of technology. Having an LLM grounded in your M365 data has obvious benifits. However, it's also worth noting that
it's likely that not all your data lives within your M365 tenant. For that scenario, there is Copilot extensibility, providiong you the ability to extent the
functionality of Copilot in a few ways. In the simplest terms Copilot extensibility allows you expand the **knowledge** (the data Copilot is grounded on) and/or the **skills** (the tasks Copilot is able to perform). Graph connectors allow you to extend the knowledge, while plugins allow you to extend knowledge and actions.
There are pros/cons to each of these options and there are definately reasons to choose one over the other, but I'll touch base on those at a later time. For now I want to focus on Graph connectors. Specifically building my own Graph connector to ingest the content I want from an external API.

Believe it or not, I am **NOT** a developer, so as I started this process I coulnd't just jump into the deep end and build a connector. I was going to have to take little steps in the
process and build up to a GC. Luckily, I do know PowerShell pretty well and understand Graph APIs so I thought that would be a great place to start. It turns out,
as a learning excersice, it was great. It allowed me to incrementially build upon what I already knew and get a simple connector built and deployed into my dev environment.

## The Plan

To start simple, my plan was as follows:

  1. Simplify process into minimal steps for a PowerShell script.
  2. Identify specific APIs and permissions needed.
  3. Find or make a sample dataset to use for development.
  4. Deploy the GC.
  5. Move on to a programming language and add more functionality.
  6. Host it in Azure App Services.
  7. Build Deployment process

Obviously, that is a bit much to put in one blog post, so I am splitting that up across several posts documenting the process including all the steps I performed with links to documentation and any code, as terrible as it may be, that I have written to build the Graph connector.

## Steps 1 and 2

These steps were pretty simple as the Graph connector development process is pretty well documented. Using [this documentation](https://learn.microsoft.com/en-us/graph/connecting-external-content-build-quickstart), I simplified the processes to 3 core steps:

1. [Create an external connection](https://learn.microsoft.com/en-us/graph/api/externalconnectors-external-post-connections?view=graph-rest-1.0&tabs=http)
2. [Register the schema](https://learn.microsoft.com/en-us/graph/api/externalconnectors-externalconnection-patch-schema?view=graph-rest-1.0&tabs=http)
3. [Write the objects to the connection.](https://learn.microsoft.com/en-us/graph/api/externalconnectors-externalconnection-put-items?view=graph-rest-1.0&tabs=http)

I now had everything I needed to get started.

First thing was to [create an app registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate%2Cexpose-a-web-api) with the correct permissions. Not a difficult task if you've ever done it before.

The important bits here are:

- ### Application (client) ID

You will get this automatically once the app registration is complete

- ### Certificates & secrets

You'll need to create either the certificate or secret here, depending on how you want to authenticate. I have a PowerShell script I've used to create [self-signed certificates](https://learn.microsoft.com/en-us/powershell/module/pki/new-selfsignedcertificate?view=windowsserver2025-ps) for use with the PowerShell Graph SDK previously so I went that route and uploaded to the app registrtaion for authentication.

- ### API Permissions

Finally, ensure you have the correct permissions assigned **AND** consented to:

![Required Graph permissions](/content/images/1-perms.png)

## The PowerShell Script

You can find my script [here](https://github.com/mattckrause/MSGraph/tree/Main/ExternalItems). I am using the Microsoft Graph PowerShell SDK and will summarize the important pieces below:

The PowerShell script authenticates against my Entra ID app registreation. I use a .env file to hold my auth data so you would need to do something similar:

```PowerShell
Function Connect_ToGraph
{
    $data = get-content -Path .env
    $appID = ($data[0].split("="))[1]
    $tenantID = ($data[1].split("="))[1]
    $authCertThumb = ($data[2].split("="))[1]

    Connect-MGGraph -ClientId $appID -TenantId $tenantID -CertificateThumbprint $authCertThumb -nowelcome
}
```

Once successfully authenticated, I then proceed to create the external connection and the schema. You'll need to pass the id, name, and description properties to the New-MgExternalConnection cmdlet to create the external connection. The schema creation is a separate task. In my script I create hashtable $schemaParams to hold the property config for the schema, and pass this to the Update-MgExternalConnectionSchema cmdlet. This is a pretty quick process, but I added a start-sleep command to pause for a few seconds between the creation of the ExternalItem and the Schema just to ensure the external connection is successfully created before attempting to register the schema.

``` PowerShell
Function New-ExternalConnection
{
    Param(
        [Parameter(Mandatory = $true,
            ValueFromPipeline = $true,
            ValueFromPipeLineByPropertyName = $true,
            ValueFromRemainingArguments = $false,
            Position = 0)]
        [ValidateNotNullOrEmpty()]
        [String]$ConnectionName
    )
    $connectionParams = @{
        id = $ConnectionName
        name = $ConnectionName
        description = "Test connector called $ConnectionName. Containing a list of company names."
    }
    $schemaParams = @{
        baseType = "microsoft.graph.externalItem"
        properties = @(
            @{
                name = "CompanyName"
                type = "String"
                isSearchable = "true"
                isRetrievable = "true"
                labels = @(
                "title"
                )
            }
        )
    }
    try{
        write-host "Creating connection $ConnectionName"
        New-MgExternalConnection -BodyParameter $connectionParams
    }
    catch{
        write-host "Error creating connection $ConnectionName"
    }
    start-sleep -s 20
    try{
        Update-MgExternalConnectionSchema -ExternalConnectionId $ConnectionName -BodyParameter $schemaParams
    }
    catch{
        write-host "Error creating schema for connection $ConnectionName"
    }
}
```

With the first two steps complete, we have the shell of a GC and are ready to write items to the created Graph connector. At this point, rather than connect to an actual external API, I used Copilot to create a very simple .CSV list of fictional companies with a discription for each. I just read that file in and process each object mapping properties to the scheam I created.

```PowerShell
Function Write-Object
{
    param (
        [Parameter(Mandatory = $true,
            ValueFromPipeline = $true,
            ValueFromPipeLineByPropertyName = $true,
            ValueFromRemainingArguments = $false,
            Position = 0)]
        [string]$externalConnectionId,
        [Parameter(Mandatory = $true,
            ValueFromPipeline = $true,
            ValueFromPipeLineByPropertyName = $true,
            ValueFromRemainingArguments = $false,
            Position = 1)]
            [string]$item,
        [Parameter(Mandatory = $true,
            ValueFromPipeline = $true,
            ValueFromPipeLineByPropertyName = $true,
            ValueFromRemainingArguments = $false,
            Position = 2)]
            [string]$externalItemId,
        [Parameter(Mandatory = $true,
            ValueFromPipeline = $true,
            ValueFromPipeLineByPropertyName = $true,
            ValueFromRemainingArguments = $false,
            Position = 3)]
            [string]$content
    )

    $params = @{
        acl = @(
            @{
                type = "everyone"
                value = "everyone"
                accessType = "grant"
            }
        )
        properties = @{
            CompanyName = $item
        }
        content = @{
            value = $content
            type = "text"
        }
}

Set-MgExternalConnectionItem -ExternalConnectionId $externalConnectionId -ExternalItemId $externalItemId -BodyParameter $params
}
```

With these 3 steps complete, we now have a Graph Connector deployed to our M365 tenant. This script doesn't include any
