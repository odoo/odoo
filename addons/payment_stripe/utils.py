# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_publishable_key(acquirer_sudo):
    """ Return the publishable key for Stripe.

    Note: This method serves as a hook for modules that would fully implement Stripe Connect.

    :param recordset acquirer_sudo: The acquirer on which the key should be read, as a sudoed
                                    `payment.acquire` record.
    :return: The publishable key
    :rtype: str
    """
    return acquirer_sudo.stripe_publishable_key


def get_secret_key(acquirer_sudo):
    """ Return the secret key for Stripe.

    Note: This method serves as a hook for modules that would fully implement Stripe Connect.

    :param recordset acquirer_sudo: The acquirer on which the key should be read, as a sudoed
                                    `payment.acquire` record.
    :return: The secret key
    :rtype: str
    """
    return acquirer_sudo.stripe_secret_key


def get_webhook_secret(acquirer_sudo):
    """ Return the webhook secret for Stripe.

    Note: This method serves as a hook for modules that would fully implement Stripe Connect.

    :param recordset acquirer_sudo: The acquirer on which the key should be read, as a sudoed
                                    `payment.acquire` record.
    :returns: The webhook secret
    :rtype: str
    """
    return acquirer_sudo.stripe_webhook_secret
