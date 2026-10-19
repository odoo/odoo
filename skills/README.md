# Odoo's Skill Library

This directory contains a set of useful Skills for agentic development with Odoo.

Skills are structured documentation that can help AI agents achieve some tasks faster
and more reliably, with less guesswork. Odoo's Skill library includes skills that
help agents review code, audit it for security, and write it right in the first place.

More about the skill format: https://agentskills.io

## Installation

The installation of the skills consists of copying the content of this directory
into the correct place, which will depend on which harness you use (claude code,
copilot-cli, codex, opencode, etc.) and where you launch it from.

The usual location is `.agents/skills/` or `.claude/skills/` at the root of
the directory where you launch your agent for Odoo development. It is also
possible to install those skills globally in your agent harness; for that,
see your harness's own documentation.

Note that all the skills provided must be installed together as they
reference each other.

## Usage

Once installed, restart your agent session and it should be able to use the
skills on its own. If you ask it _'Please review this code'_ the agent will
read the content of the `odoo-review` skill and apply its guidance.
