# GitHub Repo Setup

Target repository:

- Owner: `Tee808-bigD`
- Repo: `Agent`
- Visibility: `public`

## What to publish

This project now includes an Azure AI Toolkit starter in `azure-ai-toolkit/` with:

- agent prompt
- model profiles
- sample evals
- Azure environment template

## Suggested repository description

SimGuard Azure AI Toolkit starter with agent prompt, Azure OpenAI model profiles, and evaluation examples.

## Suggested topics

`azure-ai`
`azure-openai`
`ai-toolkit`
`agent`
`python`

## Publish commands

Run these from the project root after creating the empty public repo on GitHub:

```powershell
git init
git add .
git commit -m "Add Azure AI Toolkit starter agent setup"
git branch -M main
git remote add origin https://github.com/Tee808-bigD/Agent.git
git push -u origin main
```

## First files to show on GitHub

- `azure-ai-toolkit/README.md`
- `azure-ai-toolkit/prompts/simguard-system.prompt.md`
- `azure-ai-toolkit/model-profiles.json`

## Next improvement

Wire `backend/app/main.py` to Azure OpenAI so the repo includes both the prompt assets and a working backend integration.
