import requests


def make_gelato_request(company_id, url, data=None, method='POST'):

    headers = {
        'X-API-KEY': company_id.gelato_api_key
    }

    if method == 'POST':
        request = requests.post(url=url, json=data, headers=headers, timeout=20)
    else:
        request = requests.get(url=url, json=data, headers=headers, timeout=20)

    return request


def split_partner_name(partner_name):
    """ Split a single-line partner name in a tuple of first name, last name.

    :param str partner_name: The partner name
    :return: The split first name and last name
    :rtype: tuple
    """
    return " ".join(partner_name.split()[:-1]), partner_name.split()[-1]
