# Skill evals

Evals are unit tests for agentic scenarios. We use them to test the
performance of the Odoo skills across models and agent harnesses.

The evals are written for the [Harbor evals framework](https://docs.harborframework.com).

## Setup

- Install Docker and `harbor` (`uv tool install harbor`).
- Export `ANTHROPIC_API_KEY` (claude-code agents and the judges) and
  `OPENAI_API_KEY` (codex agents).
- Build the shared image, from this directory:

      docker build -t odoo-evals:20.0 docker

  Rebuild it when `docker/Dockerfile` changes.

## Running the evals

Run from this directory.

- Run all scenarios with the skills:

      harbor run -c all.yaml

- Run all scenarios without the skills:

      harbor run -c all-no-skills.yaml

- Run a specific set of scenarios, by task folder name:

      harbor run -c all.yaml -p . -i 'odoo-git-*'

- Name a job after what it runs, the scenario and the skills setting:

      harbor run -c all.yaml -p . -i 'odoo-stable-policy-*' --job-name stable-policy-skills

Scenarios are named `<skill>-<what is tested>`. The business case a scenario
uses (a module, a bug) is described in its README, not in its name.

## Viewing the evals

    harbor view jobs

To compare models, and the runs with and without the skills, build a report:

    python3 report/report.py jobs/<skills job> jobs/<no-skills job>
    open jobs/report.html

It plots each model's mean reward against its cost or run time per trial, with
the Pareto front, an arrow per model from its no-skills result to its skills
result, and the share of each model's error that the skills remove. Pass any
number of jobs; trials count as "with skills" when their agent had skills
attached. Claude Code reports a placeholder cost for models it has no prices
for (OpenRouter models), so the report re-prices those trials from their token
counts at OpenRouter's current list prices.
