# Skill evals

[Harbor](https://docs.harborframework.com) tasks that measure what a skill
changes in an agent's behaviour. Each task is a directory with an Odoo
checkout prepared in a state, an instruction, and a verifier that grades the
result with deterministic checks and LLM judges. A run compares harnesses and
models with and without the skill attached.

## Tasks

- `odoo-git-commit-fix-snailmail`: the checkout holds an uncommitted bug fix
  (the merged `[FIX] snailmail` commit 2a4f2233211d, applied on its parent) and
  the instruction gives the support ticket. The agent must commit it with a
  message following the odoo-git skill. Graded on the commit itself (one
  commit, same diff, clean tree), the message shape (header, wrap, ASCII,
  trailer), the message content (why first, reproduction steps leading with
  the reported case, cause, no invented facts, reviewer acceptance against the
  reference message), and the process (skill consulted, nothing else touched,
  honest final reply).
- `odoo-git-commit-fix-snailmail-no-context`: the same checkout on a branch
  named `20.0-misc-fva`, and the instruction only says "we forgot to commit,
  could you commit what's in there". Nothing names the ticket, the bug, or
  the module. It measures what the agent does with what it cannot know:
  invent it, omit it silently, or derive what the code shows and tell the
  user what is missing. The structure checks fail any reference trailer; the
  judges reward derived reproduction steps stated as such, no fabricated
  report, and a final reply that says no ticket was available and the steps
  come from the code.

## Running

Prerequisites: Docker, `harbor` (`uv tool install harbor`), and the API keys
of the agents and judges in the environment (`ANTHROPIC_API_KEY`, and
`OPENAI_API_KEY` for codex). The judges use Claude through the verifier; the
task passes `ANTHROPIC_API_KEY` to it.

Run from this directory. Validate the verifier first with the oracle, which
commits the reference message and should score close to 1:

    harbor run -p odoo-git-commit-fix-snailmail -a oracle

With the skill, every agent in the job config, one job per scenario:

    harbor run -c odoo-git-commit-with-ticket.yaml   # ticket given in the prompt
    harbor run -c odoo-git-commit-no-context.yaml    # bare "please commit" request

Each job runs Haiku 4.5, Sonnet 5 and Opus 5 on claude-code and GPT-6 Luna,
Sol and Astra on codex, three attempts each: 18 trials. Codex needs
`OPENAI_API_KEY` in the environment.

Baselines without the skill, same agents and tasks:

    harbor run -c odoo-git-commit-with-ticket-no-skill.yaml
    harbor run -c odoo-git-commit-no-context-no-skill.yaml

The process judge's "skill consulted" criterion cannot pass without the
skill, so compare the structure and message dimensions between the two
jobs, or discount that criterion from the process score.

Browse trajectories and the reward breakdown:

    harbor view jobs

The first build of the image takes a while: it installs Odoo's dependencies
the way runbot does and fetches the checkout from GitHub. Later runs reuse it;
add `--force-build` after editing the Dockerfile.

To judge with another model, set `REWARDKIT_JUDGE` in the verifier
environment: `--ve REWARDKIT_JUDGE=openai/gpt-5`.

A judge call that fails (bad key, API error) aborts the grading of that trial
and Harbor reports an exception instead of a score; rerun with
`--max-retries 2` when the API is flaky. The process dimension is skipped when
the agent left no trajectory (the oracle, or a session Harbor could not
convert); the trial's `verifier/test-stdout.txt` says so.

## Adding a task

Copy a task directory and change:

- `environment/Dockerfile`: the base commit to fetch and the branch name.
- `environment/change.patch` and `tests/change.patch`: the diff to apply
  uncommitted (`git diff <base> <fix>`). The verifier checks the commit
  carries exactly this diff.
- `instruction.md`: what the user says. Give the context a developer would
  have (ticket, task), or none to test the diff-only case.
- `tests/reference_message.txt` and `solution/reference_message.txt`: the
  reference message, without the merge-bot trailers.
- `tests/structure/*.py`: the expected tag, scope, ticket and base commit.
- `tests/message/judge.toml`: the reported scenario and cause the judge
  checks for.

Keep the merged commit unreachable from the checkout: fetch the base commit
by sha with a depth, and remove the remote.
