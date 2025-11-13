def get_iap_error_message(env, error):
    errors = {
        "not_configured": env._("Something went wrong. Try again later"),
        "no_subscription": env._("You don't have an active subscription"),
    }
    return errors.get(error, error)
