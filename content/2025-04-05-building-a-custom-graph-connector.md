---
title: My Adventure in Building a Custom Copilot Connector - Part 1
description: The process I went through in building a custom Copilot connector. Part 1 focusing on quick and dirty Powershell steps to get a custom connector up and running.
date: 2025-07-16T22:36:05.686Z
status: draft
Cover: /content/images/GCAdventure
preview: /content/images/GCAdventure.png
tags:
    - Custom Connector
    - Extensibility
    - Graph API
    - Microsoft Copilot
    - PowerShell
    - Tech Blog
categories:
    - Blog
keywords:
    - Copilot Connector
---

Microsoft Copilot is a useful piece of technology. Having a large language model (LLM) grounded in your Microsoft 365 data brings clear benefits. But it’s important to recognize that not all your data lives within your M365 tenant. That’s where Copilot extensibility steps in. It gives you the ability to expand Copilot’s functionality in a few key ways.

At a high level, Copilot extensibility lets you expand either the knowledge (the data Copilot is grounded on) or the skills (the tasks Copilot can perform). Copilot connectors (previously Graph connectors) allow you to extend Copilot’s knowledge, while plugins can extend both knowledge and actions. Each option has its pros and cons, and there are definitely scenarios where one solution makes more sense than the other, but I’ll save a detailed comparison for another post.

For now, I want to focus on Copilot connectors. More specifically, building my own custom connector to ingest some external content.

Believe it or not, I’m **NOT** a developer. So when I started this journey, I couldn’t just dive in and build a connector from scratch. I had to take it step by step. Fortunately, I am comfortable with PowerShell and familiar with Graph APIs, so that’s where I began. As a learning exercise, it turned out to be a great approach. It allowed me to build incrementally on what I already knew and ultimately get a simple connector up and running in my dev environment.

## Copilot Connector Initial Goal

To keep things manageable, I started with a simple plan:

- Identify the specific APIs and permissions required.
- Break the process down into minimal steps and build using PowerShell.
- Deploy the Copilot connector.

In additional blog posts, I'll document a more indepth process including things like:

- Migrating to a programming language to add more functionality.
- Hosting the solution in Azure App Services.
- Building a deployment process.

## Getting started

This was pretty simple as the connector development process is pretty well documented. Using [this documentation](https://learn.microsoft.com/graph/connecting-external-content-build-quickstart), I simplified the processes to 3 core steps:

1. [Create an external connection](https://learn.microsoft.com/graph/api/externalconnectors-external-post-connections?view=graph-rest-1.0&tabs=http)
2. [Register the schema](https://learn.microsoft.com/graph/api/externalconnectors-externalconnection-patch-schema?view=graph-rest-1.0&tabs=http)
3. [Write the objects to the connection.](https://learn.microsoft.com/graph/api/externalconnectors-externalconnection-put-items?view=graph-rest-1.0&tabs=http)

In order to build using Microsoft Graph, we need to authenticate using the correct permissions. We can do this by [creating an app registration](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app?tabs=certificate%2Cexpose-a-web-api) through Microsoft Entra and using that information as part of our authentication flow.

The important bits here are:

- ## Application (client) ID

You will get this automatically once the app registration process is complete. It can be found in the *Overview* section on the left.

- ## Certificates & secrets

You'll need to create either the certificate or secret here, depending on how you want to authenticate. You can use PowerShell to create [self-signed certificates](https://learn.microsoft.com/powershell/module/pki/new-selfsignedcertificate?view=windowsserver2025-ps) for use with the Graph PowerShell SDK.

- ## API Permissions

You'll need to ensure you have the correct permissions assigned **AND** consented to. The required permissions (from documentation above) are:

- ExternalConnection.ReadWrite.OwnedBy
- ExternalItem.ReadWriet.OwnedBy

![Image showing the required Graph permissions shown in the app registration including that they have been granted admin consent]({attach}/images/1-perms.png)

## The PowerShell Commands

The [Graph PowerShell SDK](https://learn.microsoft.com/powershell/microsoftgraph/installation?view=graph-powershell-1.0) provides an easy method to authenticate using the Entra app registreation previously created. For security purposes, I use a .env file to hold my auth data so I don't store any credentials in plain text. I've included two code snippets to show authentication using both Certificates and secrets. The snippets read the .env file and passes the appID, tenantID and certificate thumbprint/client secret to the **Connect-MgGraph** cmdlet:

```PowerShell
#Authentication using Certificate
$data = get-content -Path .env
$appID = ($data[0].split("="))[1]
$tenantID = ($data[1].split("="))[1]
$authCertThumb = ($data[2].split("="))[1]

Connect-MgGraph -ClientId $appID -TenantId $tenantID -CertificateThumbprint $authCertThumb -nowelcome
```

```PowerShell
#Authentication using client secret
$data = get-content -Path .env
$appID = ($data[0].split("="))[1]
$tenantID = ($data[1].split("="))[1]
$clientSecret = ($data[2].split("="))[1]

$securedPassword = ConvertTo-SecureString `
-String $clientSecret -AsPlainText -Force

$clientsecretCredential = New-Object `
-TypeName System.Management.Automation.PSCredential `
-ArgumentList $appID, $securedPassword

Connect-MgGraph -TenantId $tenantID -ClientSecretCredential $clientsecretCredential -nowelcome
```

Once successfully authenticated, you can verify the session permissions by running the **Get-MgContext** cmdlet ensuring you see the permissions consented to previously:

![Results from the PowerShell Get-MGContext cmdlet]({attach}/images/1-get_mgcontext.png)

Now that you have successfuly authenticated, the next step is to creat the external connection. Think of this as an empty container that will eventually hold the Schema configuration and the ingested external items. The necessary cmdlet from the Graph PowerShell SDK is **New-MgExternalConnection**. You'll need to pass in three values: the Name, ID, and Description for the Copilot Connector:

``` PowerShell
$connectionName = "TestCopilotConnector"
$connectionParams = @{
    id = $ConnectionName
    name = $ConnectionName
    description = "Test connector called $ConnectionName. Containing a list of company names."
}

New-MgExternalConnection -BodyParameter $connectionParams
```

With the external connection created, the next step is to define the schema and update the external connection with that schema data:

```PowerShell
#create schema
$connectionName = "TestCopilotConnector"

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

Update-MgExternalConnectionSchema -ExternalConnectionId $ConnectionName -BodyParameter $schemaParams
```

⭐⭐ **It should be noted at this point that the Schema creation process can take between 5 and 15 minutes. The documentation recomends using the location response header to get the current status of the schema creation operation** ⭐⭐

With the first two steps complete, you have the shell of a Copilot connector and are ready to write items. Rather than connect to an actual external API, to keep this first attempt simple, I used Copilot to create a .CSV list of fictional companies with a discription for each. The script reads that .CSV file and creates new items for each object, mapping properties to the simple schema I created, using a GUID as the item ID and setting the ACL to allow access for everyone:

```PowerShell
Import-Csv -Path "C:\github\MyScripts\GraphAPI\PS_SDK\ExternalItems\fictitious_companies.csv" | ForEach-Object {
        $params = @{
            acl = @(
                @{
                    type = "everyone"
                    value = "everyone"
                    accessType = "grant"
                }
            )
            properties = @{
                CompanyName = $_.name
            }
            content = @{
                value = $_.description
                type = "text"
            }
        }
    Set-MgExternalConnectionItem -ExternalConnectionId "test" -ExternalItemId (New-Guid) -BodyParameter $params
}
```

## Conclusion

Obviously, this isn't intended to be a full blown Copilot connector. But it does provide the general process and it should help you to get your own Copilot connector up and running with relatively little effort. I have used PowerShell scripts based on this learning a handful of times to help get samples up and running quickly for testing and demos. I am providing a [sample script](https://github.com/mattckrause/MSGraph/tree/Main/ExternalItems) I've written as an example of how you might put it all together. As previously mentioned, this is the first post of a series where I build upon these learning to create a Copilot connector using Python that is hosted in Azure app services and enabled for Copilot consumption.
