#!/usr/bin/env python3
"""Three deterministic local demonstrations. Python 3.10+, standard library.
No network, uploads, credentials, external inputs, file writes or automatic retries.
MIT License: Copyright (c) 2026 AgentCollabSpace contributors.
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies, subject to retaining this
notice. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM OR DAMAGES.
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math


def retry_after_seconds(value, reference):
    """Parse integer delay or HTTP-date; reference is an aware response receipt time.
    None means unrecognized input, not permission to retry immediately.
    This helper does not implement backoff, clock-skew correction or authorization.
    """
    if not isinstance(value, str) or reference.tzinfo is None:
        return None
    value = value.strip()
    if value.isascii() and value.isdigit():
        return int(value) if len(value) <= 10 else None
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            return None
        return max(0, math.ceil((date-reference).total_seconds()))
    except (ValueError, TypeError, OverflowError):
        return None


def retry_after_demo():
    reference = datetime(2026,9,17,12,0,0,tzinfo=timezone.utc)
    inputs = ['30','Thu, 17 Sep 2026 12:00:30 GMT','invalid','-1','1.5']
    return {'reference_time':reference.isoformat(),
            'seconds':[retry_after_seconds(v, reference) for v in inputs],
            'inputs':inputs,'meaning':'Parsing a delay does not authorize a retry.'}


def timeout_demo():
    def simulate(deduplicated, second_key):
        effects, receipts = [], {}
        def write(key, drop_response=False):
            if deduplicated and key in receipts:
                return receipts[key]
            effects.append('synthetic-effect')
            receipt = {'operation':len(effects)}
            receipts[key] = receipt
            if drop_response:
                raise TimeoutError('Synthetic response loss after commit')
            return receipt
        try: write('saved-key', drop_response=True)
        except TimeoutError: pass
        receipt = write(second_key)
        return {'committed_effects':len(effects),'returned_operation':receipt['operation']}
    return {'no_deduplication':simulate(False,'saved-key'),
            'same_key_with_deduplication':simulate(True,'saved-key'),
            'new_key_with_deduplication':simulate(True,'new-key'),
            'limits':'In-memory model with permanent receipts, no concurrency. Real services have scope, retention and payload rules.'}


def pagination_demo():
    initial = [5,4,3,2,1]
    first = initial[:2]
    after_delete = [5,3,2,1]  # item 4 disappears after page 1
    offset = after_delete[2:4]
    cursor = [i for i in after_delete if i < first[-1]][:2]
    return {'first_page':first,'after_delete':after_delete,
            'offset_second_page':offset,'cursor_second_page':cursor,
            'missed_existing_item_by_offset':3,
            'limits':'Unique immutable descending IDs in this model. Cursor pagination alone is not a snapshot and cannot recover deleted content.'}


DEMOS = {'retry-after':retry_after_demo,'timeout-after-write':timeout_demo,'pagination-drift':pagination_demo}
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario', choices=DEMOS)
    args = parser.parse_args()
    print(json.dumps(DEMOS[args.scenario](),indent=2))
