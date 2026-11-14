#!/usr/bin/env python3
"""Build an HTML report comparing models across harbor jobs.

The report plots each model's mean reward against its mean cost or run time
per trial, marks the Pareto front, and, when the jobs hold runs both with and
without skills, shows what the skills change for each model (reward, cost,
time, error reduction).

Trials are split into "with skills" and "without skills" by whether their agent
had skills attached, so pass a skills job and its no-skills baseline together:

    python3 report/report.py jobs/all-full-run jobs/all-without-skills

Averages weigh every task the same: a model's trials are averaged per task,
then the task averages are averaged. Errored trials are left out.

Claude Code has no prices for models it does not know (OpenRouter models such
as GLM or Kimi) and reports a placeholder cost for them, marked
costBasis "unknown". Those trials are re-priced from their token counts at
OpenRouter's current list prices, fetched on each run.
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OPENROUTER_MODELS = 'https://openrouter.ai/api/v1/models'

_openrouter = None


def openrouter_rates():
    """{model id: (input, cache read, cache write, output)} in USD per token."""
    global _openrouter
    if _openrouter is None:
        _openrouter = {}
        try:
            with urllib.request.urlopen(OPENROUTER_MODELS, timeout=20) as resp:
                for m in json.load(resp)['data']:
                    p = m.get('pricing') or {}
                    prompt = float(p.get('prompt') or 0)
                    _openrouter[m['id']] = (
                        prompt,
                        float(p.get('input_cache_read') or prompt),
                        float(p.get('input_cache_write') or prompt),
                        float(p.get('completion') or 0),
                    )
        except Exception as e:  # noqa: BLE001
            print(f'warning: could not fetch OpenRouter prices ({e}); keeping reported costs', file=sys.stderr)
    return _openrouter


def agent_seconds(result):
    """Wall-clock seconds of the agent run (excludes setup and verification)."""
    phase = result.get('agent_execution') or {}
    try:
        start, end = (datetime.fromisoformat(phase[k].replace('Z', '+00:00')) for k in ('started_at', 'finished_at'))
    except (KeyError, TypeError, ValueError):
        return None
    return (end - start).total_seconds()


def claude_code_usage(trial_dir):
    """modelUsage from the final result event Claude Code printed, or None."""
    path = os.path.join(trial_dir, 'agent', 'claude-code.txt')
    if not os.path.exists(path):
        return None
    usage = None
    for line in open(path, errors='replace'):
        if '"type":"result"' not in line:
            continue
        try:
            usage = json.loads(line).get('modelUsage')
        except ValueError:
            pass
    return usage


def reprice(trial_dir):
    """Re-price a Claude Code trial whose cost Claude Code guessed (costBasis "unknown").

    Returns (cost, {model: rates}), or None when the reported cost can be kept.
    """
    usage = claude_code_usage(trial_dir)
    if not usage or not any(u.get('costBasis') == 'unknown' for u in usage.values()):
        return None
    rates_by_id = openrouter_rates()
    total, used = 0.0, {}
    for model, u in usage.items():
        if u.get('costBasis') != 'unknown':
            total += u.get('costUSD') or 0.0
            continue
        rates = rates_by_id.get(model)
        if rates is None:
            return None
        i, cr, cw, o = rates
        total += (u.get('inputTokens', 0) * i + u.get('cacheReadInputTokens', 0) * cr
                  + u.get('cacheCreationInputTokens', 0) * cw + u.get('outputTokens', 0) * o)
        used[model] = rates
    return total, used


def load_job(job_dir, trials, errors, price_notes):
    """Append the job's trials and errored trials; return its summary."""
    variants = set()
    for path in sorted(glob.glob(os.path.join(job_dir, '*', 'result.json'))):
        r = json.load(open(path))
        variant = 'skills' if r['config']['agent'].get('skills') else 'none'
        variants.add(variant)
        model = r['config']['agent']['model_name']
        task = r['task_id']['path']
        exc = r.get('exception_info')
        rewards = (r.get('verifier_result') or {}).get('rewards') or {}
        if exc or 'reward' not in rewards:
            msg = str((exc or {}).get('exception_message') or 'no verifier result')
            m = re.search(r'"result":"(API Error[^"]*)"', msg)
            errors.append({'model': model, 'task': task, 'variant': variant,
                           'reason': m.group(1) if m else (exc or {}).get('exception_type', 'error')})
            continue
        reported = (r.get('agent_result') or {}).get('cost_usd') or 0.0
        repriced = reprice(os.path.dirname(path)) if r['config']['agent']['name'] == 'claude-code' else None
        if repriced:
            for m, rates in repriced[1].items():
                price_notes[m] = [round(x * 1e6, 4) for x in rates]
        trials.append({
            'model': model,
            'variant': variant,
            'agent': r['config']['agent']['name'],
            'task': task,
            'trial': r['trial_name'],
            'reward': rewards['reward'],
            'cost': repriced[0] if repriced else reported,
            'reported_cost': reported,
            'estimated': bool(repriced),
            'time': agent_seconds(r),
        })

    stats = {}
    job_result = os.path.join(job_dir, 'result.json')
    if os.path.exists(job_result):
        jr = json.load(open(job_result))
        stats = {k: jr.get('stats', {}).get(k)
                 for k in ('n_completed_trials', 'n_errored_trials', 'n_running_trials', 'n_pending_trials')}
        stats['n_total_trials'] = jr.get('n_total_trials')
    return {'name': os.path.basename(os.path.normpath(job_dir)), 'variants': sorted(variants), 'stats': stats}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('jobs', nargs='+', metavar='JOB_DIR', help='harbor job directories, e.g. jobs/all-full-run')
    parser.add_argument('-o', '--output', default=os.path.join(HERE, '..', 'jobs', 'report.html'),
                        help='HTML file to write (default: jobs/report.html)')
    parser.add_argument('--fragment', action='store_true',
                        help='omit the <!doctype html> skeleton, for hosts that wrap the page themselves')
    args = parser.parse_args()

    trials, errors, price_notes, jobs = [], [], {}, []
    for job_dir in args.jobs:
        if not os.path.isdir(job_dir):
            parser.error(f'not a directory: {job_dir}')
        jobs.append(load_job(job_dir, trials, errors, price_notes))
    if not trials:
        parser.error('no finished trials found in the given jobs')

    data = {
        'jobs': jobs,
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'trials': trials,
        'errors': errors,
        'openrouter_rates': price_notes,
    }
    html = open(os.path.join(HERE, 'template.html')).read()
    html = html.replace('__DATA__', json.dumps(data).replace('</', '<\\/'))
    if not args.fragment:
        html = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '<style>body { margin: 0; font-size: 14px; }</style>\n') + html
    output = os.path.normpath(args.output)
    with open(output, 'w') as f:
        f.write(html)

    for j in jobs:
        print(f"{j['name']}: {', '.join(j['variants'])}")
    n_est = sum(t['estimated'] for t in trials)
    print(f'{len(trials)} trials ({n_est} re-priced at OpenRouter rates), {len(errors)} errored -> {output}')


if __name__ == '__main__':
    main()
