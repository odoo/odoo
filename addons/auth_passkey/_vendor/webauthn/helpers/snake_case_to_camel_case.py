def snake_case_to_camel_case(snake_case: str) -> str:
    """
    Helper method for converting a snake_case'd value to camelCase

    input: pub_key_cred_params
    output: pubKeyCredParams
    """
    parts = snake_case.split("_")
    converted = parts[0].lower() + "".join(part.title() for part in parts[1:])

    # Massage "clientDataJson" to "clientDataJSON"
    converted = converted.replace("Json", "JSON")

    return converted
