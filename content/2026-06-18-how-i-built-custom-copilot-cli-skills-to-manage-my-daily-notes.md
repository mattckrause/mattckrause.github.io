---
title: How I Built Custom Copilot CLI Skills to Manage My Daily Notes
description: A walkthrough of how I built custom skills for GitHub Copilot CLI that integrate Obsidian notes with Microsoft 365 data through WorkIQ, saving me real time every day.
date: 2026-06-18 10:00
status: draft
tags: Copilot CLI, Obsidian, WorkIQ, Productivity, Microsoft 365, Skills
keywords: Copilot CLI skills, Obsidian automation, WorkIQ, daily notes
category: Tech Blog
cover: ""
---

***

I take a lot of notes. Like, a lot. Between customer calls, 1:1s, team meetings, and the random "I should remember this" moments throughout the day, my Obsidian vault is where everything lives. The problem is, keeping it all organized and making sure nothing falls through the cracks used to take real effort. I'd finish a call, jot some bullets, and then spend another 10 minutes routing those notes to the right customer files, creating follow-up tasks, and cross-referencing what was discussed against emails and Teams messages I might have missed.

That's time I don't have. So I built something to help.

Over the past few months, I've been building custom skills for GitHub Copilot CLI that integrate my Obsidian vault with my Microsoft 365 data through WorkIQ. The result is a workflow where I can process a meeting, have the notes automatically routed to the right places, get tasks created in Planner, and cross-reference M365 data — all from my terminal. It genuinely saves me time every single day.

Here's how I built it and the design decisions that made it actually useful.

***

## The Problem I Was Solving

Here's what my workflow used to look like: I'd get off a customer call, open Obsidian, and try to remember everything that was discussed. Then I'd need to figure out *where* those notes should go. Is this a customer note? A project note? Does it touch multiple customers? Do I need to update my daily note too?

Then there were the action items. I'd write them in the customer note, but then I'd also need to go create them in Planner so they'd show up in my task board. And half the time I'd forget one, or I'd create a task for something that wasn't really actionable yet — just a vague "look into this" that would sit in my Planner untouched for weeks.

And emails. Someone would mention in a call "I sent you the details last week" and I'd have to go hunt through my inbox to find what they were talking about. More context switching. More time spent on overhead instead of actual work.

The core pain points were:

- **Manual routing** — figuring out which notes go where, every single time
- **Context switching** — bouncing between Obsidian, Planner, Outlook, and Teams
- **Things slipping** — action items that never made it to my task board, follow-ups I forgot about
- **Duplicate effort** — writing notes AND creating tasks AND updating my daily log, all separately

I knew I wanted something that could handle all of this in one shot. One command, and everything lands where it should.

***

## What Are Copilot CLI Skills?

If you're not familiar with GitHub Copilot CLI, it's basically an AI assistant that lives in your terminal. You can ask it questions, have it run commands, edit files, search your codebase — all the stuff you'd expect. But out of the box, it doesn't know anything about *your* specific workflows. It doesn't know how you organize your notes, what tools you use, or what your conventions are.

That's where skills come in.

A skill is a Markdown file (called `SKILL.md`) that you drop into `~/.copilot/skills/<skill-name>/`. It gives Copilot CLI specialized instructions for a specific domain. Think of it like writing a really detailed onboarding doc for a new team member — except the team member is an AI that will actually follow it to the letter.

Here's what a skill file typically contains:

- **Where things live** — file paths, folder structures, naming conventions
- **How to do things** — step-by-step procedures, decision trees, routing logic
- **When to do things** — trigger phrases, conditions, edge cases
- **What NOT to do** — guardrails, common mistakes to avoid

The key insight is that skills aren't code. They're instructions written in plain English (with some Markdown structure). You're basically teaching the AI your workflow in the same way you'd explain it to a human — just with more precision around edge cases.

Once a skill is in place, Copilot CLI automatically activates it when your request matches the skill's description. Say something like "process my last call" and it knows to use the M365 skill. Say "what are my open tasks" and it reaches for the Obsidian skill. You don't have to explicitly invoke anything — it just works.

***

## Skill #1: Obsidian Notes — Teaching Copilot My Vault

The first skill I built was the foundation: teaching Copilot CLI how my Obsidian vault is structured and how I want notes managed.

### The Key Design Decisions

The most important thing I learned early on is that **the skill needs to understand your conventions, not just your file paths.** It's not enough to say "my notes are in this folder." You need to tell it:

- How files are named and organized
- What the templates look like
- Where new content should be inserted (and where it shouldn't)
- How to handle ambiguity

Here's what the core vault structure definition looks like:

```markdown
**Vault path:** `C:\Users\makrause\OneDrive - Microsoft\Obsidian\Work`

## Vault structure

Work/
├── Daily Notes/          # Daily journal entries (one per day)
├── Customers/CAD/        # Customer engagement notes (one file per customer)
├── Templates/            # Note templates
├── One on Ones/          # 1:1 meeting notes
└── Archive/              # Archived/older notes
```

But the real value is in the **content routing logic**. This is what turns a generic "add notes" capability into something that actually knows where things go:

```markdown
#### Content routing and multi-topic notes

Before writing content, classify each meaningful bullet by its actual
topic/project/customer, not only by the meeting title or first matching note.

1. Identify candidate target notes first.
2. Split mixed-topic content across notes.
3. Use the daily note as an index.
4. Ask when routing is ambiguous.
5. Avoid duplicate detail.
```

<!-- Write about: Why content routing was the breakthrough. Before this, everything got dumped into one note. Now the skill splits mixed-topic meetings across the right customer/project files automatically. Give a concrete example — like a team meeting where 3 customers get discussed. -->

This was the single biggest breakthrough in making the skill actually useful. Before I added this logic, the skill would just dump everything into whatever note seemed closest to the meeting title. Had a team standup where five different customers came up? All of it ended up in one messy note.

Now, the skill searches my vault for candidate notes before writing anything. If a standup covers Contoso's schema issues, Fabrikam's timeline question, and an internal project update, it writes each chunk to the appropriate file — `Customers/CAD/Contoso.md`, `Customers/CAD/Fabrikam.md`, and the project note respectively — and links all three from my daily note. The daily note becomes a clean index of the day, not a dumping ground.

### Task Classification

Another design decision that paid off was teaching the skill to classify action items before creating tasks:

```markdown
- #todo — specific, actionable item with a clear deliverable
- #investigate — requires research before a real action can be defined
- #follow-up — checking status, nudging someone, waiting on input
```

Only `#todo` items get Planner tasks created. This prevents my task board from getting clogged with "look into this eventually" items that aren't actually actionable yet.

Before I added this classification, my Planner board was a mess. I'd have 30+ tasks, and half of them were things like "explore feasibility of X" or "check back with Y next month." They'd sit there forever, making it impossible to see what I actually needed to do *today*. Now my Planner only has real, actionable work with clear deliverables. The investigate and follow-up items still exist in Obsidian — they're not lost — but they stay out of my task board until they graduate to something concrete.

***

## Skill #2: WorkIQ Integration — Connecting M365 Data

The second skill extends the first by pulling in data from Microsoft 365. Through WorkIQ, the skill can:

- Pull meeting transcripts and process them into structured notes
- Look up recent emails and Teams messages for context
- Cross-reference what was discussed against what's in my inbox
- Create Planner tasks directly from action items

WorkIQ is essentially the data bridge between Copilot CLI and your M365 tenant. It gives the skill access to the same stuff you'd normally dig through manually — calendar events, transcripts, emails, Teams chats. The difference is now I can say "what did so-and-so email me about last week?" and get an answer without leaving my terminal.

But the real magic is when you combine it with the Obsidian skill.

### The "Process My Last Call" Workflow

This is probably the thing I use most. After a customer call, I open my terminal and say something like:

```
"Process my last call with Contoso"
```

That's it. One sentence. Here's what happens behind the scenes:

**Step 1: Fetch the transcript.** The skill calls WorkIQ to pull the full meeting transcript from Teams, including speaker names and timestamps. It validates that it got the right meeting — checking attendees, date, and topic against what I asked for. If something looks off, it stops and asks me to confirm before proceeding.

**Step 2: Extract the good stuff.** The raw transcript gets parsed into structured notes:

- Attendees
- Key discussion points (the actual substance, not the small talk)
- Decisions that were made
- Action items — split by owner and classified by type
- Open questions that still need answers

**Step 3: Route to the right notes.** This is where the Obsidian skill takes over. The structured content gets written to `Customers/CAD/Contoso.md` as a new date entry at the top of the file:

```markdown
- [[June 18 2026]]
	- Attendees: Matt, Sarah, Dev Team
	- Discussion:
		- Reviewed connector schema changes for production
		- Discussed timeline for Phase 2 rollout
	- Decisions:
		- Moving forward with simplified schema (3 properties)
	- My Action Items:
		- [ ] Send updated schema documentation to Sarah by Friday #todo
		- [ ] Investigate whether their HRIS system exposes a REST API #investigate
	- Others' Action Items:
		- Confirm IT has provisioned the app registration (@Sarah)
	- Open Questions:
		- Are they planning to use the connector for Copilot only, or also Search? #follow-up
```

**Step 4: Update the daily note.** Today's daily note gets a link added — `- [[Contoso]]` — so it serves as an index of what I worked on that day.

**Step 5: Create Planner tasks.** Only the `#todo` items (the ones with a clear deliverable) get pushed to Microsoft Planner as private tasks. In this example, "Send updated schema documentation to Sarah by Friday" becomes a Planner task titled "Contoso: Send updated schema documentation to Sarah" with a due date of Friday and a note pointing back to the Obsidian file.

The `#investigate` and `#follow-up` items stay in Obsidian only. They're visible, they're tracked, but they don't clutter my task board until they become real, actionable work.

**Step 6: Confirm with me.** Finally, the skill reports back what it did — a quick summary of what was extracted, where it was saved, and which Planner tasks were created. If I notice something got misrouted or misclassified, I can fix it right there.

### What This Actually Looks Like Day-to-Day

On a typical day, I have 4-6 customer calls or internal meetings. Before I built this, I'd finish a call and spend 10-15 minutes manually writing up notes, figuring out which file to put them in, creating tasks, and cross-referencing emails. Now I spend about 30 seconds per call — just long enough to say "process my last call" and confirm the output looks right.

That's conservatively 40-60 minutes saved per day on note-taking alone. And honestly, the bigger win isn't the time — it's that things don't fall through the cracks anymore. Every action item gets captured. Every customer discussion lands in the right file. My daily note always has a complete picture of what I worked on.

<!-- Write about: Add a specific anecdote if you have one — a time the skill caught something you would have missed, or a time the content routing surprised you by correctly splitting a complex meeting across 3 different notes. -->

***

## What I Learned Building These

Building these skills was very much an iterative process. The first version of my Obsidian skill was maybe 20 lines — just the vault path and a basic "here's how to add notes" instruction. It worked, sort of. But it made mistakes constantly. It would write to the wrong file, overwrite existing content, or dump everything under a single heading regardless of context.

Here are the lessons that got me from "kinda works" to "actually reliable":

### Start simple, then add rules for every mistake

Every guardrail in my skill file exists because I watched it do something wrong. The "read before write" rule? That's because it once overwrote half a customer note. The content routing logic? That came after it dumped a 5-customer standup into one file. The task classification? Because my Planner was unusable.

The approach is basically: use it, watch it fail, add a rule, repeat. Over time, the skill gets smarter because you're encoding your own judgment into it.

### Be absurdly specific about formatting

I learned quickly that "use the same format" isn't good enough. You need to show exact examples with exact indentation. Tabs vs. spaces matters. Whether a date is `[[June 18 2026]]` or `[[Jun 18, 2026]]` matters. The skill follows what you show it, so if your examples are sloppy, your output will be too.

### "Read before write" is non-negotiable

This one bit me early. The skill would happily create a new date entry even if one already existed for today, resulting in duplicate blocks. Now the first instruction for any write operation is: **read the current file first.** Check what's there. Then decide where to insert or append. It seems obvious in hindsight, but it's the kind of thing you have to be explicit about.

### Testing is just... using it

There's no unit test framework for skills. The testing loop is: make a change to the skill file, use it in a real scenario, see if it does what you expect. If it doesn't, adjust the instructions and try again. It's more like training than traditional development. Expect to iterate a lot in the first few weeks, and then it stabilizes as you cover the common edge cases.

***

## The Time Savings Are Real

I don't want to oversell this, but the numbers speak for themselves. On a typical day I have 4-6 meetings that generate notes. Before the skills, each one cost me 10-15 minutes of post-meeting overhead — writing up notes, routing them, creating tasks, checking emails for context. That's easily an hour or more per day spent on organizational busywork.

Now it's about 30 seconds per meeting. Say the magic words, confirm the output, move on.

**Conservative math:**

- 5 meetings/day × 10 minutes saved = **50 minutes/day**
- That's roughly **4 hours/week** I've gotten back
- Over a month, that's basically **two full working days**

But honestly, the time savings aren't even the biggest win. The real value is:

- **Nothing falls through the cracks.** Every action item gets captured and classified. Every discussion gets routed to the right place. My future self can actually find things.
- **Less cognitive load.** I don't have to hold meeting notes in my head while I figure out where they go. That mental energy goes toward the actual work instead.
- **Better follow-through.** Because tasks automatically appear in Planner with due dates and context, I'm way more likely to actually do them. And because open questions are tagged as `#follow-up`, I don't forget to circle back.
- **Complete daily notes.** At the end of any given day, I can look at my daily note and see exactly what I worked on, who I talked to, and what came out of it. That's been surprisingly valuable for weekly reports and performance reviews.

***

## Conclusion

If you've read this far, you might be thinking "that's cool, but my workflow is different." And it is — that's actually the whole point. Skills are personal. They encode *your* conventions, *your* folder structure, *your* quirks. The specific routing logic I built won't work for you, but the approach absolutely will.

Here's what I'd suggest if you want to try this:

1. **Identify your repetitive overhead.** What do you do after every meeting that feels mechanical? That's your candidate.
2. **Start with one skill, one task.** Don't try to automate everything at once. My first version just added notes to the right file. That's it.
3. **Iterate based on real usage.** Use it every day. When it does something wrong, add a rule. When it does something right, leave it alone.
4. **Be specific about formatting.** Show don't tell. Include exact examples in your skill file.

I'm considering sharing a starter template for the skill structure — something stripped of my specific vault details that others could use as a jumping-off point. If that would be useful to you, let me know.

In the meantime, if you're drowning in meeting notes and spending more time organizing than thinking, maybe this gives you some ideas. It's not perfect, and I'm still tweaking it, but it's turned what used to be a daily grind into something that mostly just happens in the background. And that's been worth every minute I spent building it.
