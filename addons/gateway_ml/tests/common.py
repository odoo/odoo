def endpoint_by_code(env, code):
    endpoint = env["integration.service"].search([("code", "=", code)], limit=1)
    if not endpoint:
        raise AssertionError(
            f"no integration.service carries the code {code!r}. AI endpoints "
            f"are addressed by vendor code — the key gateway.ml.provider.code "
            f"uses — never by "
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


def disconnect(env, provider):
    services = provider.service_ids.service_id.filtered(
        lambda service: service.auth_type != "none"
    )
    env["integration.connection"].search(
        [("service_id", "in", services.ids)]
    ).action_archive()
    return services


def connect(env, provider, key="the-key"):
    for service in disconnect(env, provider):
        secret = "api_key" if service.auth_type == "api_key" else "bearer_token"
        credential_for(
            env,
            service.code,
            environment=service.environment,
            company_id=env.company.id,
            **{secret: key},
        )
