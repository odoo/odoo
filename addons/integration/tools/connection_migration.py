import logging

_logger = logging.getLogger(__name__)


def connect_bound_credentials(env) -> dict[str, list[str]]:
    credentials = (
        env["credential.credential"]
        .sudo()
        .with_context(active_test=False)
        .search([("endpoint_id", "!=", False)])
    )
    env["integration.connection"]._sync_from_credentials(credentials)

    aligned, unresolved = [], []
    services = (
        env["integration.service"].sudo().with_context(active_test=False).search([])
    )
    for service in services:
        environments = set(
            service.connection_ids.filtered("active").mapped("environment")
        )
        if not environments or service.environment in environments:
            continue
        if len(environments) == 1:
            (environment,) = environments
            _logger.info(
                "integration: service %s used its %s connection, not its own %s "
                "environment; the service now says %s",
                service.code,
                environment,
                service.environment,
                environment,
            )
            service.environment = environment
            aligned.append(service.code)
        else:
            unresolved.append(service.code)
    if unresolved:
        _logger.warning(
            "integration: no connection in their own environment, and connections in "
            "several others, so nothing resolves until one is chosen: %s",
            ", ".join(sorted(unresolved)),
        )
    return {"aligned": aligned, "unresolved": unresolved}
