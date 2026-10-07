def clean_node_dict(node, template=None):
    """Clean a UBL-style node dictionary by removing child nodes not defined in the template.
    Attributes and metadata (like '_text', 'CurrencyID', 'SchemeID') are preserved.

    :param node: dict representing the node
    :param template: dict defining allowed child keys
    :return: cleaned node dict
    """
    if not isinstance(node, dict) or template is None:
        return node

    for child_tag, child in list(node.items()):
        # Skip special keys or simple attributes
        if child_tag.startswith('_') or not isinstance(child, (dict, list)):
            continue

        # Remove child if not in template
        if child_tag not in template:
            node.pop(child_tag)
            continue

        child_template = template.get(child_tag)

        if isinstance(child, dict):
            # Recursive cleaning for dict children
            cleaned_child = clean_node_dict(child, template=child_template)
            node[child_tag] = cleaned_child

        elif isinstance(child, list):
            cleaned_list = []
            for item in child:
                if isinstance(item, dict):
                    cleaned_item = clean_node_dict(item, template=child_template)
                    cleaned_list.append(cleaned_item)
                else:
                    # If item is not a dict, keep as is
                    cleaned_list.append(item)
            node[child_tag] = cleaned_list

    return node
