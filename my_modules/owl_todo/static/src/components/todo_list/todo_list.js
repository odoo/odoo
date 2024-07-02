/* @odoo-module */

import { registry } from "@web/core/registry";
const { Component, useState, onWillStart, useRef } = owl;
import { useService } from "@web/core/utils/hooks";


export class OwlTodo extends Component {
    setup() {
        this.state = useState({
        tasklist:[],
        task:{name:"", color:"#ffffff", completed:false},
        idEdit: false,
        activeId: false,
    })

    this.orm = useService("orm")
    this.model = "owl.todo.list"
    this.searchInput = useRef("search-input")

    onWillStart(async ()=>{
        await this.getAllTask()
    })

    }

    async getAllTask(){
        this.state.tasklist = await this.orm.searchRead(this.model, [], ["name", "color", "completed"])
    }

    addTask(){
        this.resetForm()
        this.state.activeId = false
        this.state.isEdit = false
    }

    editTask(task){
        this.state.activeId = task.id
        this.state.isEdit = true
        this.state.task = {...task}
    }


    async saveTask(){

        if(!this.state.isEdit){
            await this.orm.create(this.model, [this.state.task])
        } else {
            await this.orm.write(this.model, [this.state.activeId], this.state.task)
        }

        await this.getAllTask()
    }
    resetForm(){
        this.state.task = {name:"", color:"#000000", completed:false}
    }

    async deleteTask(task){
        this.orm.unlink(this.model, [task.id])

        await this.getAllTask()
    }

    async searchTask(){
        const text= this.searchInput.el.value
        this.state.tasklist =await this.orm.searchRead(this.model, [['name','ilike', text]],["name", "color", "completed"])
    }

    async toggleTask(e, task){
        await this.orm.write(this.model, [task.id], {completed: e.target.checked})
        await this.getAllTask()
    }


    async updateColor(e, task){
        await this.orm.write(this.model, [task.id], {color: e.target.value})
        await this.getAllTask()
    }


}

OwlTodo.template = 'Owl.TodoList';

registry.category("actions").add("owl_todo_list_action_views_js", OwlTodo);