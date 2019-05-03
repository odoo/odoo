""" View validation code (using assertions, not the RNG schema). """

import collections
import logging
import os

from lxml import etree
from odoo import tools

_logger = logging.getLogger(__name__)


_validators = collections.defaultdict(list)
_relaxng_cache = {}

def valid_view(arch):
    for pred in _validators[arch.tag]:
        check = pred(arch)
        if not check:
            _logger.error("Invalid XML: %s", pred.__doc__)
            return False
        if check == "Warning":
            _logger.warning("Invalid XML: %s", pred.__doc__)
            return "Warning"
    return True


def validate(*view_types):
    """ Registers a view-validation function for the specific view types
    """
    def decorator(fn):
        for arch in view_types:
            _validators[arch].append(fn)
        return fn
    return decorator


def relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        with tools.file_open(os.path.join('base', 'rng', '%s_view.rng' % view_type)) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception('Failed to load RelaxNG XML schema for views validation')
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


@validate('calendar', 'diagram', 'gantt', 'graph', 'pivot', 'search', 'tree', 'activity')
def schema_valid(arch):
    """ Get RNG validator and validate RNG file."""
    validator = relaxng(arch.tag)
    if validator and not validator.validate(arch):
        result = True
        for error in validator.error_log:
            _logger.error(tools.ustr(error))
            result = False
        return result
    return True

@validate('form')
def valid_page_in_book(arch):
    """A `page` node must be below a `notebook` node."""
    return not arch.xpath('//page[not(ancestor::notebook)]')


@validate('graph')
def valid_field_in_graph(arch):
    """ Children of ``graph`` can only be ``field`` """
    return all(
        child.tag == 'field'
        for child in arch.xpath('/graph/*')
    )


@validate('tree')
def valid_field_in_tree(arch):
    """ Children of ``tree`` view must be ``field`` or ``button`` or ``control`` or ``groupby``."""
    return all(
        child.tag in ('field', 'button', 'control', 'groupby')
        for child in arch.xpath('/tree/*')
    )


@validate('form', 'graph', 'tree', 'activity')
def valid_att_in_field(arch):
    """ ``field`` nodes must all have a ``@name`` """
    return not arch.xpath('//field[not(@name)]')


@validate('form')
def valid_att_in_label(arch):
    """ ``label`` nodes must have a ``@for`` """
    return not arch.xpath('//label[not(@for) and not(descendant::input)]')


@validate('form')
def valid_att_in_form(arch):
    return True


@validate('form')
def valid_type_in_colspan(arch):
    """A `colspan` attribute must be an `integer` type."""
    return all(
        attrib.isdigit()
        for attrib in arch.xpath('//@colspan')
    )


@validate('form')
def valid_type_in_col(arch):
    """A `col` attribute must be an `integer` type."""
    return all(
        attrib.isdigit()
        for attrib in arch.xpath('//@col')
    )

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_alternative_image_text(arch):
    """An `img` tag must have an alt value."""
    if arch.xpath('//img[not(@alt or @t-att-alt or @t-attf-alt)]'):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_alternative_icon_text(arch):
    """An icon with fa- class or in a button must have aria-label in its tag, parents, descendants or have text."""
    valid_aria_attrs = {
        'aria-label', 'aria-labelledby', 't-att-aria-label', 't-attf-aria-label',
        't-att-aria-labelledby', 't-attf-aria-labelledby'}
    valid_t_attrs = {'t-value', 't-raw', 't-field', 't-esc'}
    valid_attrs = valid_aria_attrs | valid_t_attrs
    valid_aria_attrs_xpath = ' or '.join('@' + attr for attr in valid_aria_attrs)
    valid_attrs_xpath = ' or '.join('@' + attr for attr in valid_attrs)

    # Select elements with class begining by 'fa-'
    xpath = '(//*[contains(concat(" ", @class), " fa-")'
    xpath += ' or contains(concat(" ", @t-att-class), " fa-")'
    xpath += ' or contains(concat(" ", @t-attf-class), " fa-")]'
    xpath += ' | //button[@icon])'
    # Elements with accessibility or string attrs are good
    xpath += '[not(' + valid_attrs_xpath + ')]'
    # And we ignore all elements with describing in children
    xpath += '[not(//*[' + valid_attrs_xpath + '])]'
    # Aria label can be on ancestors
    xpath += '[not(ancestor[' + valid_aria_attrs_xpath + '])]'
    # Labels provide text by definition
    xpath += '[not(descendant-or-self::label)]'
    # Buttons can have a string attribute
    xpath += '[not(descendant-or-self::button[@string])]'
    # Fields have labels
    xpath += '[not(descendant-or-self::field)]'
    # And finally, if there is some text, it's good too
    xpath += '[not(descendant-or-self::*[text()])]'
    # Following or preceding text
    xpath += '[not(preceding-sibling::text()[normalize-space()])]'
    xpath += '[not(following-sibling::text()[normalize-space()])]'
    # Following or preceding text in span
    xpath += '[not(preceding-sibling::span[text()])]'
    xpath += '[not(following-sibling::span[text()])]'

    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_title_icon(arch):
    """An icon with fa- class or in a button must have title in its tag, parents, descendants or have text."""
    valid_title_attrs = {'title', 't-att-title', 't-attf-title'}
    valid_t_attrs = {'t-value', 't-raw', 't-field', 't-esc'}
    valid_attrs = valid_title_attrs | valid_t_attrs
    valid_title_attrs_xpath = ' or '.join('@' + attr for attr in valid_title_attrs)
    valid_attrs_xpath = ' or '.join('@' + attr for attr in valid_attrs)

    # Select elements with class begining by 'fa-'
    xpath = '(//*[contains(concat(" ", @class), " fa-")'
    xpath += ' or contains(concat(" ", @t-att-class), " fa-")'
    xpath += ' or contains(concat(" ", @t-attf-class), " fa-")]'
    xpath += ' | //button[@icon])'
    # Elements with accessibility or string attrs are good
    xpath += '[not(' + valid_attrs_xpath + ')]'
    # And we ignore all elements with describing in children
    xpath += '[not(//*[' + valid_attrs_xpath + '])]'
    # Aria label can be on ancestors
    xpath += '[not(ancestor[' + valid_title_attrs_xpath + '])]'
    # Labels provide text by definition
    xpath += '[not(descendant-or-self::label)]'
    # Buttons can have a string attribute
    xpath += '[not(descendant-or-self::button[@string])]'
    # Fields have labels
    xpath += '[not(descendant-or-self::field)]'
    # And finally, if there is some text, it's good too
    xpath += '[not(descendant-or-self::*[text()])]'
    # Following or preceding text
    xpath += '[not(preceding-sibling::text()[normalize-space()])]'
    xpath += '[not(following-sibling::text()[normalize-space()])]'
    # Following or preceding text in span
    xpath += '[not(preceding-sibling::span[text()])]'
    xpath += '[not(following-sibling::span[text()])]'

    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_simili_button(arch):
    """A simili button must be tagged with "role='button'"."""
    # Select elements with class 'btn'
    xpath = '//a[contains(concat(" ", @class), " btn")'
    xpath += ' or contains(concat(" ", @t-att-class), " btn")'
    xpath += ' or contains(concat(" ", @t-attf-class), " btn")]'
    xpath += '[not(@role="button")]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_simili_dropdown(arch):
    """A simili dropdown must be tagged with "role='menu'"."""
    xpath = '//*[contains(concat(" ", @class, " "), " dropdown-menu ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " dropdown-menu ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " dropdown-menu ")]'
    xpath += '[not(@role="menu")]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_simili_progressbar(arch):
    """A simili progressbar must be tagged with "role='progressbar'" and have
    aria-valuenow, aria-valuemin and aria-valuemax attributes."""
    # Select elements with class 'btn'
    xpath = '//*[contains(concat(" ", @class, " "), " o_progressbar ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " o_progressbar ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " o_progressbar ")]'
    xpath += '[not(self::progress)]'
    xpath += '[not(@role="progressbar")]'
    xpath += '[not(@aria-valuenow or @t-att-aria-valuenow or @t-attf-aria-valuenow)]'
    xpath += '[not(@aria-valuemin or @t-att-aria-valuemin or @t-attf-aria-valuemin)]'
    xpath += '[not(@aria-valuemax or @t-att-aria-valuemax or @t-attf-aria-valuemax)]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_dialog(arch):
    """A dialog must use role="dialog" and its header, body and footer contents must use <header/>, <main/> and <footer/>."""
    # Select elements with class 'btn'
    xpath = '//*[contains(concat(" ", @class, " "), " modal ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " modal ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " modal ")]'
    xpath += '[not(@role="dialog")]'
    if arch.xpath(xpath):
        return "Warning"

    xpath = '//*[contains(concat(" ", @class, " "), " modal-header ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " modal-header ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " modal-header ")]'
    xpath += '[not(self::header)]'
    if arch.xpath(xpath):
        return "Warning"

    xpath = '//*[contains(concat(" ", @class, " "), " modal-body ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " modal-body ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " modal-body ")]'
    xpath += '[not(self::main)]'
    if arch.xpath(xpath):
        return "Warning"

    xpath = '//*[contains(concat(" ", @class, " "), " modal-footer ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " modal-footer ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " modal-footer ")]'
    xpath += '[not(self::footer)]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_simili_tabpanel(arch):
    """A tab panel with tab-pane class must have role="tabpanel"."""
    # Select elements with class 'btn'
    xpath = '//*[contains(concat(" ", @class, " "), " tab-pane ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " tab-pane ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " tab-pane ")]'
    xpath += '[not(@role="tabpanel")]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_simili_tab(arch):
    """A tab link must have role="tab", a link to an id (without #) by aria-controls."""
    # Select elements with class 'btn'
    xpath = '//*[@data-toggle="tab"]'
    xpath += '[not(@role="tab")'
    xpath += 'or not(@aria-controls or @t-att-aria-controls or @t-attf-aria-controls)'
    xpath += 'or contains(@aria-controls, "#") or contains(@t-att-aria-controls, "#")]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_simili_tablist(arch):
    """A tab list with class nav-tabs must have role="tablist"."""
    # Select elements with class 'btn'
    xpath = '//*[contains(concat(" ", @class, " "), " nav-tabs ")'
    xpath += ' or contains(concat(" ", @t-att-class, " "), " nav-tabs ")'
    xpath += ' or contains(concat(" ", @t-attf-class, " "), " nav-tabs ")]'
    xpath += '[not(@role="tablist")]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_focusable_button(arch):
    """A simili button must be with a `button`, an `input` (with type `button`, `submit` or `reset`) or a `a` tag."""
    xpath = '//*[contains(concat(" ", @class), " btn")'
    xpath += ' or contains(concat(" ", @t-att-class), " btn")'
    xpath += ' or contains(concat(" ", @t-attf-class), " btn")]'
    xpath += '[not(self::a)]'
    xpath += '[not(self::button)]'
    xpath += '[not(self::select)]'
    xpath += '[not(self::input[@type="button"])]'
    xpath += '[not(self::input[@type="submit"])]'
    xpath += '[not(self::input[@type="reset"])]'
    xpath += '[not(contains(@class, "btn-group"))]'
    xpath += '[not(contains(@t-att-class, "btn-group"))]'
    xpath += '[not(contains(@t-attf-class, "btn-group"))]'
    xpath += '[not(contains(@class, "btn-toolbar"))]'
    xpath += '[not(contains(@t-att-class, "btn-toolbar"))]'
    xpath += '[not(contains(@t-attf-class, "btn-toolbar"))]'
    xpath += '[not(contains(@class, "btn-ship"))]'
    xpath += '[not(contains(@t-att-class, "btn-ship"))]'
    xpath += '[not(contains(@t-attf-class, "btn-ship"))]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_prohibited_none_role(arch):
    """A role can't be `none` or `presentation`. All your elements must be accessible with screen readers, describe it."""
    xpath = '//*[@role="none" or @role="presentation"]'
    if arch.xpath(xpath):
        return "Warning"
    return True

@validate('calendar', 'diagram', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
def valid_alerts(arch):
    """An alert (class alert-*) must have an alert, alertdialog or status role. Please use alert and alertdialog only for what expects to stop any activity to be read immediatly."""
    xpath = '//*[contains(concat(" ", @class), " alert-")'
    xpath += ' or contains(concat(" ", @t-att-class), " alert-")'
    xpath += ' or contains(concat(" ", @t-attf-class), " alert-")]'
    xpath += '[not(contains(@class, "alert-link") or contains(@t-att-class, "alert-link")'
    xpath += ' or contains(@t-attf-class, "alert-link"))]'
    xpath += '[not(@role="alert")]'
    xpath += '[not(@role="alertdialog")]'
    xpath += '[not(@role="status")]'
    if arch.xpath(xpath):
        return "Warning"
    return True
