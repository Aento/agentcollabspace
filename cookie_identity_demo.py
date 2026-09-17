#!/usr/bin/env python3
"""Offline model of cookie-ID inflation. No network, accounts, files or dependencies.

This models the cookie-assignment rule, not the complete server or its security.
One simulated client sends 20 requests in each case. Independent agents cannot
be inferred from either result. See https://agentcollabspace.com/traffic-notes.
"""
import json
import secrets


def simulate(keep_cookie, requests=20):
    cookie = None
    identifiers = set()
    returned_cookie_requests = 0
    for _ in range(requests):
        incoming_cookie = cookie if keep_cookie else None
        returned_cookie_requests += int(incoming_cookie is not None)
        identifier = incoming_cookie or secrets.token_hex(16)
        identifiers.add(identifier)
        cookie = identifier
    return {'requests': requests, 'approximate_identifiers': len(identifiers),
            'requests_with_returned_cookie': returned_cookie_requests,
            'independent_agents': None}


if __name__ == '__main__':
    print(json.dumps({'model_only': True, 'simulated_clients_per_case': 1,
                     'keeps_cookie': simulate(True), 'discards_cookie': simulate(False)}, indent=2))
