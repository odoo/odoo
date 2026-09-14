def endpoint_by_code(env, code):
    endpoint = env["integration.service"].search([("code", "=", code)], limit=1)
    if not endpoint:
        raise AssertionError(
            f"no integration.service carries the code {code!r}. AI endpoints "
            f"are addressed by vendor code — the key vendor_catalog.PROVIDERS, "
            f"AI_CLIENT_REGISTRY and ai.provider.code all use — never by "
            f"external id, which is free to be renamed without touching a wire.",
        )
    return endpoint


def credential_for(env, code, **vals):
    return env["credential.credential"].create(
        {
            "name": f"{code} key",
            "endpoint_id": endpoint_by_code(env, code).id,
            **vals,
        },
    )
