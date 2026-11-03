{
    'name': "Build Your Party - website",
    'summary': "Huisstijl, header, footer en pagina's voor Build Your Party",
    'description': """
De presentatielaag van de website: kleuren, typografie, een eigen header en
footer over de hele site, en de pagina's Home, Onze diensten, Over ons en
Professionals. Nagebouwd op de proof of concept van Bosh & Bordon
(byp.bbstaging4.be), zodat de marketingpagina's en de tool op dezelfde site
staan en de bezoeker overal ziet dat hij ingelogd is.

Logo's, mascottes en foto's horen in static/src/img, met de bestandsnamen
die de templates gebruiken.

Bewust een aparte module van `event_builder`. Die laatste is de
boekingsmotor en moet los te installeren blijven; deze module gaat alleen
over hoe het eruitziet. Zo kan je de configurator later ook op een andere
website of onder een andere huisstijl draaien.

Alles staat in code: een deploy zet de site in de juiste staat, en een
module-upgrade herstelt hem. Er is bewust GEEN `oe_structure` in de
vastgelegde zones, zodat de website-builder er niet in kan.
    """,
    'author': "Sander",
    'category': 'Website/Website',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',

    'depends': [
        'website',
        'event_builder',
    ],

    'data': [
        'views/layout.xml',
        'views/homepage.xml',
        'views/tool.xml',
        'views/pages.xml',
        'data/website_data.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'byp_website/static/src/scss/byp_website.scss',
            'byp_website/static/src/js/byp_floating_cta.js',
        ],
    },

    'installable': True,
}
