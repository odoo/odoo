<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

<t t-inherit="website.BuilderOptions" t-inherit-mode="extension">
    <xpath expr="//t[@id='page_options_hook']" position="after">
        <navbar_logo_option
            template="website.NavbarLogoOption"
            selector="#wrapwrap > header nav.navbar .navbar-brand"
            title="Navbar Logo"
            groups='["website.group_website_designer"]'
            editableOnly="false"/>
        <header_template_option
            selector="#wrapwrap > header"
            editableOnly="false"
            groups='["website.group_website_designer"]'/>
        <top_menu_visibility_option
            selector="[data-main-object]:has(input.o_page_option_data[name='header_visible']) #wrapwrap > header"
            editableOnly="false"
            groups='["website.group_website_designer"]'/>
        <header_font_option
            template="website.HeaderFontOption"
            selector="#wrapwrap > header"
            editableOnly="false"
            groups='["website.group_website_designer"]'/>
        <header_box_option
            selector="#wrapwrap > header"
            applyTo=".navbar:not(.d-none)"
            editableOnly="false"
            groups='["website.group_website_designer"]'/>
        <language_selector_option
            template="website.LanguageSelectorOption"
            selector="#wrapwrap > header nav.navbar .o_header_language_selector"
            groups='["website.group_website_designer"]'
            reloadTarget="true"
            editableOnly="false"/>
        <header_navigation_option
            selector="#wrapwrap > header"
            editableOnly="false"
            reloadTarget="true"
            groups='["website.group_website_designer"]'/>
        <header_elements_option
            selector="#wrapwrap > header"
            editableOnly="false"
            groups='["website.group_website_designer"]'/>
        <header_icon_background_option
            template="website.HeaderIconBackgroundOption"
            selector="#wrapwrap > header"
            editableOnly="false"
            groups='["website.group_website_designer"]'/>
    </xpath>
</t>

</templates>
