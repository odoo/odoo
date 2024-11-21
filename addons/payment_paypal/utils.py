# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_normalized_email_account(provider):
    """ Remove unicode characters, such as \u200b coming from pasted emails, from the provider's
    paypal email account.

    :return: The normalized address of the paypal email account of the provider.
    :rtype: str
    """
    return provider.paypal_email_account.encode('ascii', 'ignore').decode('utf-8')
