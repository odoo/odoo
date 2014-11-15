import copy
import logging

import openerp.tests

_logger = logging.getLogger(__name__)

@openerp.tests.common.post_install(True)
class TestSync(openerp.tests.TransactionCase):
    """
    Test for synchronization, synchroniztion is too complex, so that's why make sure it doesn't break anything,
    Test the synchroniztion with completely new record with new project, new task and nre record, //Done
    Test the synchroniztion with existing hr.analytic.timesheet record but with new project and task, //Done
    Test the synchroniztion with exisiting record update, //Done
    Test the synchroniztion with new record with exisitng project and task, //Done
    Test the synchronization with record which is already having reference_id in database, sync twice to skip duplication
    """
    def setUp(self):
        super(TestSync, self).setUp()
        self.sequence = 0
        self.hr_analytic_timesheet_model = self.registry('hr.analytic.timesheet')
        self.project_timesheet_session_model = self.registry('project.timesheet.session')
        self.project_model = self.registry('project.project')
        self.task_model = self.registry('project.task')

    def generate_reference(self):
        cr, uid = self.cr, self.uid
        session_detail = self.project_timesheet_session_model.get_session(cr, uid)
        self.sequence += 1
        return str(session_detail.get('session_id', 1)) + "-" + str(session_detail.get("login_number", 1)) + "-" + str(self.sequence)

    def test_sync(self):
        cr, uid = self.cr, self.uid
        project_id= False
        task_id = False
        projects = self.project_model.name_search(cr, uid, "The Jackson")
        if projects:
            project_id = projects[0]
        tasks = self.task_model.name_search(cr, uid, "Integrate Modules")
        if tasks:
            task_id = tasks[0]
        datas = [{'project_id': ['virtual_id_1', 'Test Project 1'], 'task_id': ['virtual_id_2', 'Test Task 1'], 'unit_amount': 10, 'command': 0, 'user_id': uid, 'date': '2014-11-10', 'name': 'Test Activity 1', 'reference_id': self.generate_reference()},
                 {'project_id': project_id, 'task_id': task_id, 'unit_amount': 12.5, 'command': 0, 'user_id': uid, 'date': '2014-11-10', 'name': 'Test Activity 2', 'reference_id': self.generate_reference()},
                 ]
        sync_result = self.hr_analytic_timesheet_model.sync_data(cr, uid, datas)
        if sync_result.get('activities'):
            _logger.info("testing sync data successful")

        search_result = self.hr_analytic_timesheet_model.search(cr, uid, [('name', '=', 'Test Activity 1')])
        _logger.info("testing sync data exisitng_record is %s", search_result)
        if search_result:
            exisiting_record = self.hr_analytic_timesheet_model.read(cr, uid, search_result[0])
            exisiting_record.update({'project_id': project_id, 'task_id': task_id, 'unit_amount': 20, 'command': 1})
            sync_result = self.hr_analytic_timesheet_model.sync_data(cr, uid, [exisiting_record])
            _logger.info("testing sync data update project and task successful")

        reference_id = self.generate_reference()
        check_sync_twice = [{'project_id': ['virtual_id_1', 'Test Project 1'], 'task_id': ['virtual_id_2', 'Test Task 1'], 'unit_amount': 10, 'command': 0, 'user_id': uid, 'date': '2014-11-10', 'name': 'Test Activity 3', 'reference_id': reference_id}]
        record1 = copy.deepcopy(check_sync_twice)
        sync_result = self.hr_analytic_timesheet_model.sync_data(cr, uid, record1)
        record2 = copy.deepcopy(check_sync_twice)
        sync_result = self.hr_analytic_timesheet_model.sync_data(cr, uid, record2)
        if len(self.hr_analytic_timesheet_model.search(cr, uid, [('reference_id', '=', reference_id)])) == 1:
            _logger.info("testing sync data sync same record twice is successful")
        else:
            _logger.info("testing sync data: sync twice fails, it creates duplicate records")
        