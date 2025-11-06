from odoo import http
from odoo.http import request

class TaskManagerController(http.Controller):

    @http.route("/task_manager/tasks", type="json", auth="user")
    def get_tasks(self):
        tasks = request.env["task.manager"].search([])
        return [{"id": t.id, "name": t.name, "is_done": t.is_done} for t in tasks]

    @http.route("/task_manager/add_task", type="json", auth="user")
    def add_task(self, name):
        task = request.env["task.manager"].create({"name": name})
        return {"id": task.id, "name": task.name, "is_done": task.is_done}

    @http.route("/task_manager/toggle_task", type="json", auth="user")
    def toggle_task(self, id, is_done):
        task = request.env["task.manager"].browse(id)
        task.is_done = is_done
        return True
    
    @http.route("/task_manager/delete_task", type="json", auth="user")
    def delete_task(self, id):
        task = request.env["task.manager"].browse(id)
        if task.exists():
            task.unlink()
        return True
