# -*- coding: utf-8 -*-

{
    'name': 'Pokédex',
    'version': '1.0',
    'author': 'Richard Mathot',
    'category': 'Misc',
    'description': """
Manage your Pokémon Team in Odoo.

This module is (of course) a joke.

**All Pokemon-names, pictures, and stuff related to these games still belong to
Nintendo & their original authors.**

- Datas inspired from: https://github.com/veekun/pokedex/tree/master/pokedex/data/csv
- Pokémon sprites have been found there: http://veekun.com/dex/downloads
""",
    'depends': ['base'],
    'data': [
        'views/pokedex.xml',
        'data/pokedex.type.csv',
        'data/pokedex.pokemon.csv',
        'data/pokemon_sprites.xml',
    ],
    'application': True,
    'installable': True,
}
