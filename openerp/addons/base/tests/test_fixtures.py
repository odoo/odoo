# -*- coding: utf-8 -*-
import pytest

@pytest.fixture
def partner_name():
    return 'test_per_class_teardown_partner'

def test_00(env, partner_name):
    """Create a partner."""
    partners = env['res.partner'].search([('name', '=', partner_name)])
    assert len(partners) == 0, "Found unexpected test partner"

    env['res.partner'].create({'name': partner_name})

    partners = env['res.partner'].search([('name', '=', partner_name)])
    assert len(partners) == 1, "Test partner not found."

def test_01(env, partner_name):
    """Don't find the created partner."""
    partners = env['res.partner'].search([('name', '=', partner_name)])
    assert len(partners) == 0, "Test partner found."

def test_02(env):
    """ Create a partner with a XML ID then resolve xml id with ref() and browse_ref() """
    Partners = env['res.partner']
    ModelData = env['ir.model.data']
    pid, _ = Partners.name_create('Mr Yellow')
    partner_xid = 'test_partner_yellow'
    ModelData.create({
        'name': partner_xid,
        'module': 'base',
        'model': 'res.partner',
        'res_id': pid})
    partner = env.ref('base.{}'.format(partner_xid))
    assert partner.name == 'Mr Yellow'
