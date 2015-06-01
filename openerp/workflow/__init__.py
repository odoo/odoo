# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.workflow.service import WorkflowService

# The new API is in openerp.workflow.workflow_service
# OLD API of the Workflow

def clear_cache(cr, uid):
    WorkflowService.clear_cache(cr.dbname)

def trg_write(uid, res_type, res_id, cr):
    """
    Reevaluates the specified workflow instance. Thus if any condition for
    a transition have been changed in the backend, then running ``trg_write``
    will move the workflow over that transition.

    :param res_type: the model name
    :param res_id: the model instance id the workflow belongs to
    :param cr: a database cursor
    """
    return WorkflowService.new(cr, uid, res_type, res_id).write()

def trg_trigger(uid, res_type, res_id, cr):
    """
    Activate a trigger.

    If a workflow instance is waiting for a trigger from another model, then this
    trigger can be activated if its conditions are met.

    :param res_type: the model name
    :param res_id: the model instance id the workflow belongs to
    :param cr: a database cursor
    """
    return WorkflowService.new(cr, uid, res_type, res_id).trigger()

def trg_delete(uid, res_type, res_id, cr):
    """
    Delete a workflow instance

    :param res_type: the model name
    :param res_id: the model instance id the workflow belongs to
    :param cr: a database cursor
    """
    return WorkflowService.new(cr, uid, res_type, res_id).delete()

def trg_create(uid, res_type, res_id, cr):
    """
    Create a new workflow instance

    :param res_type: the model name
    :param res_id: the model instance id to own the created worfklow instance
    :param cr: a database cursor
    """
    return WorkflowService.new(cr, uid, res_type, res_id).create()

def trg_validate(uid, res_type, res_id, signal, cr):
    """
    Fire a signal on a given workflow instance

    :param res_type: the model name
    :param res_id: the model instance id the workflow belongs to
    :signal: the signal name to be fired
    :param cr: a database cursor
    """
    assert isinstance(signal, basestring)
    return WorkflowService.new(cr, uid, res_type, res_id).validate(signal)

def trg_redirect(uid, res_type, res_id, new_rid, cr):
    """
    Re-bind a workflow instance to another instance of the same model.

    Make all workitems which are waiting for a (subflow) workflow instance
    for the old resource point to the (first active) workflow instance for
    the new resource.

    :param res_type: the model name
    :param res_id: the model instance id the workflow belongs to
    :param new_rid: the model instance id to own the worfklow instance
    :param cr: a database cursor
    """
    assert isinstance(new_rid, (long, int))
    return WorkflowService.new(cr, uid, res_type, res_id).redirect(new_rid)
