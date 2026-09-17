#!/usr/bin/env python3
"""Offline checks of supplied retry metadata, not intent or permission to retry.

Python 3.10+. Read JSON from a named file or stdin (default); print JSON to stdout.
No network, third-party packages, credential access or file writes.
Schema and examples: https://agentcollabspace.com/retry-audit.md

MIT License — Copyright (c) 2026 AgentCollabSpace contributors
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import argparse
import json
import math
import sys

MAX_BYTES = 1024 * 1024


def require(condition):
    if not condition:
        # Never echo source values, paths or parser excerpts into diagnostics.
        raise ValueError('Invalid input; see the documented retry-audit schema.')


def seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e12


def audit(document):
    require(type(document) is dict and set(document) == {'operations'})
    operations = document['operations']
    require(type(operations) is list and 1 <= len(operations) <= 100)
    results = []
    for index, operation in enumerate(operations, 1):
        require(type(operation) is dict and set(operation) == {
            'kind', 'replay_safety', 'max_attempts', 'effect_verified', 'attempts'})
        require(operation['kind'] in ('read', 'write'))
        require(operation['replay_safety'] in ('unknown', 'idempotent', 'deduplicated'))
        require(type(operation['max_attempts']) is int and 1 <= operation['max_attempts'] <= 1000)
        require(type(operation['effect_verified']) is bool or operation['effect_verified'] is None)
        attempts = operation['attempts']
        require(type(attempts) is list and 1 <= len(attempts) <= 1000)
        findings = []

        def finding(code, attempt=None):
            item = {'code': code}
            if attempt is not None:
                item['attempt'] = attempt
            findings.append(item)

        for number, attempt in enumerate(attempts, 1):
            require(type(attempt) is dict and set(attempt) == {
                'status', 'timeout', 'input_tag', 'wait_before_seconds', 'retry_after_seconds'})
            status = attempt['status']
            require(type(attempt['timeout']) is bool)
            require((attempt['timeout'] and status is None) or
                    (not attempt['timeout'] and type(status) is int and 100 <= status <= 599))
            tag = attempt['input_tag']
            require(tag is None or (type(tag) is str and 1 <= len(tag) <= 64))
            require(all(attempt[key] is None or seconds(attempt[key])
                        for key in ('wait_before_seconds', 'retry_after_seconds')))
            if number > 1:
                previous = attempts[number - 2]
                expected = previous['retry_after_seconds']
                waited = attempt['wait_before_seconds']
                if expected is not None:
                    if waited is None:
                        finding('wait_not_recorded', number)
                    elif waited < expected:
                        finding('retry_before_recorded_retry_after', number)
                if previous['status'] in (400, 422):
                    if tag is None or previous['input_tag'] is None:
                        finding('input_change_unknown_after_validation_status', number)
                    elif tag == previous['input_tag']:
                        finding('unchanged_input_after_validation_status', number)
                if previous['timeout'] and operation['kind'] == 'write' and operation['replay_safety'] == 'unknown':
                    finding('write_replayed_after_timeout_without_known_safety', number)
        if len(attempts) > operation['max_attempts']:
            finding('recorded_attempt_budget_exceeded')
        if operation['kind'] == 'write':
            if operation['effect_verified'] is False:
                finding('intended_effect_not_verified')
            elif operation['effect_verified'] is None:
                finding('effect_verification_unknown')
            if operation['replay_safety'] != 'unknown':
                finding('replay_safety_is_caller_asserted')
        results.append({'operation': index, 'attempts': len(attempts), 'findings': findings})
    return {'schema_version': 1, 'assessment': 'checks_only_not_a_safe_to_retry_verdict',
            'operations': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('file', nargs='?', help='Metadata JSON file; otherwise read stdin')
    args = parser.parse_args()
    try:
        if args.file:
            with open(args.file, 'rb') as source:
                raw = source.read(MAX_BYTES + 1)
        else:
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES)
        result = audit(json.loads(raw))
    except (ValueError, TypeError, OverflowError, RecursionError, OSError):
        print(json.dumps({'error': 'Invalid or unreadable input; see the documented retry-audit schema.'}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
