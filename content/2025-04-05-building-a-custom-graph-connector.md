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

Microsoft Copilot is a useful piece of technology. Having a large language model (LLM) grounded in your Microsoft 365 data brings clear benefits. But it’s important to recognize that not all your data lives within your M365 tenant. That’s where Copilot extensibility steps in. It gives you the ability to expand Copilot’s functionality in a few key ways.

At a high level, Copilot extensibility lets you expand either the knowledge (the data Copilot is grounded on) or the skills (the tasks Copilot can perform). Graph connectors allow you to extend Copilot’s knowledge, while plugins can extend both knowledge and actions. Each option has its pros and cons, and there are definitely scenarios where one makes more sense than the other—but I’ll save that full comparison for another post.

For now, I want to focus on Graph connectors—specifically, building my own to ingest content from an external API.

Believe it or not, I’m **NOT** a developer. So when I started this journey, I couldn’t just dive in and build a connector from scratch. I had to take it step by step. Fortunately, I am comfortable with PowerShell and familiar with Graph APIs, so that’s where I began. As a learning exercise, it turned out to be a great approach. It allowed me to build incrementally on what I already knew and ultimately get a simple connector up and running in my dev environment.

## The End Goal

To keep things manageable, I started with a simple plan:

1. Identify the specific APIs and permissions required.
2. Break the process down into minimal steps using PowerShell.
3. Create or find a sample dataset for development.
4. Deploy the Graph Connector.
5. Transition to a programming language to add more functionality.
6. Host the solution in Azure App Services.
7. Build a deployment process.

Clearly, that’s too much to cover in a single blog post. So I’m breaking it up into a series of posts that walk through each step of the process. I’ll include links to relevant documentation and share any code I’ve written as I build out the Graph Connector.

## Steps 1 and 2 covered in this blog post

These steps were pretty simple as the Graph connector development process is pretty well documented. Using [this documentation](https://learn.microsoft.com/en-us/graph/connecting-external-content-build-quickstart), I simplified the processes to 3 core steps:

1. [Create an external connection](https://learn.microsoft.com/en-us/graph/api/externalconnectors-external-post-connections?view=graph-rest-1.0&tabs=http)
2. [Register the schema](https://learn.microsoft.com/en-us/graph/api/externalconnectors-externalconnection-patch-schema?view=graph-rest-1.0&tabs=http)
3. [Write the objects to the connection.](https://learn.microsoft.com/en-us/graph/api/externalconnectors-externalconnection-put-items?view=graph-rest-1.0&tabs=http)

I now had everything I needed to get started.

First thing was to [create an app registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate%2Cexpose-a-web-api) with the correct permissions.

The important bits here are:

- ### Application (client) ID

You will get this automatically once the app registration is complete

- ### Certificates & secrets

You'll need to create either the certificate or secret here, depending on how you want to authenticate. I have a PowerShell script I've used to create [self-signed certificates](https://learn.microsoft.com/en-us/powershell/module/pki/new-selfsignedcertificate?view=windowsserver2025-ps) for use with the PowerShell Graph SDK previously so I went that route and uploaded to the app registrtaion for authentication.

- ### API Permissions

Finally, ensure you have the correct permissions assigned **AND** consented to:

![Required Graph permissions](/content/images/1-perms.png)

## The PowerShell Script

You can find my full script [here](https://github.com/mattckrause/MSGraph/tree/Main/ExternalItems). I am using the Microsoft Graph PowerShell SDK and will summarize the important pieces below:

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

Once successfully authenticated, I then proceed to create the external connection and the schema. You'll need to pass the id, name, and description properties to the New-MgExternalConnection cmdlet to create the external connection. The schema creation is a separate task. In my script I create a hashtable *$schemaParams* to hold the property config for the schema, and pass this to the Update-MgExternalConnectionSchema cmdlet. This is a pretty quick process, but I added a start-sleep command to pause for a few seconds between the creation of the ExternalItem and the Schema just to ensure the external connection is successfully created before attempting to register the schema.

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
    start-sleep -s 5
    try{
        Update-MgExternalConnectionSchema -ExternalConnectionId $ConnectionName -BodyParameter $schemaParams
    }
    catch{
        write-host "Error creating schema for connection $ConnectionName"
    }
}
```

It should be noted at this point that the Schema creation process can take between 5 and 15 minutes. The documentation recomends using the location response header to get the current status of the schema creation operation.

With the first two steps complete, we have the shell of a Graph connector and are ready to write items to the created Graph connector. Rather than connect to an actual external API, to keep this first attempt simple, I used Copilot to create a .CSV list of fictional companies with a discription for each. The script reads that file in and processes each object mapping properties to the scheam I created.

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

We've looked at the 3 functions I built and now we can see how I call each of the functions:

```PowerShell
#Main Script
Connect-ToGraph

$ConnectionName = "PowerShellGraphConnector"

if ($Process.ToLower() -eq "install")
{
    New-ExternalConnection -ConnectionName $ConnectionName
}
elseif ($Process.ToLower() -eq "uninstall")
{
    Remove-ExternalConnection -ConnectionName $ConnectionName
}
elseif ($Process.ToLower() -eq "writeitems")
{
    Import-Csv -Path "C:\fictitious_companies.csv" | ForEach-Object {
        Write-Object -externalConnectionId $ConnectionName -item $_.name -externalItemId $_.name -content $_.description
    } 
}
else
{
    Write-Host "Invalid process specified. Use 'install','uninstall', or 'writeitems."
}

#Disconnect from Graph when complete!
Disconnect-MGGraph
```

To run the script you would call the script passing in a paramater for what you wish to do. For example:

``` PowerShell
New-GraphConnector.ps1 -Install
```

 Available parameters for the script incldue:

- install
- uninstall
- writeitems

---

And just like that, I have a simple Graph connector build using PowerShell that I can use to ingest external items into my tenant.
