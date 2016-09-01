# -*- coding: utf-8 -*-
#
#
#    Authors: Guewen Baconnier
#    Copyright 2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import importlib
from contextlib import contextmanager

import mock


@contextmanager
def mock_job_delay_to_direct(job_path):
    """ Replace the .delay() of a job by a direct call

    job_path is the python path as string, such as::

      'openerp.addons.magentoerpconnect.stock_picking.export_picking_done'

    This is a context manager, all the calls made to the job function in
    job_path inside the context manager will be executed synchronously.

    .. note:: It uses :meth:`mock.patch` so it has the same pitfall
              regarding the python path.  If the mock seems to have no
              effect, read `Where to patch
              <http://www.voidspace.org.uk/python/mock/patch.html#where-to-patch>`_
              in the mock documentation.

    """
    job_module, job_name = job_path.rsplit('.', 1)
    module = importlib.import_module(job_module)
    job_func = getattr(module, job_name, None)
    assert job_func, "The function %s must exist in %s" % (job_name,
                                                           job_module)

    def clean_args_for_func(*args, **kwargs):
        # remove the special args reserved to '.delay()'
        kwargs.pop('priority', None)
        kwargs.pop('eta', None)
        kwargs.pop('model_name', None)
        kwargs.pop('max_retries', None)
        kwargs.pop('description', None)
        job_func(*args, **kwargs)

    with mock.patch(job_path) as patched_job:
        # call the function directly instead of '.delay()'
        patched_job.delay.side_effect = clean_args_for_func
        yield patched_job
