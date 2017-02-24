odoo.define('minerva.js', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var base = require('web_editor.base');  
    
    var qweb = core.qweb;
    qweb.add_template('/minerva/static/src/xml/template1.xml');
    
    
    function renderTemplate(template_id, data, location_id){
        var loader = $(qweb.render(template_id, data));
        loader.appendTo(location_id);
    }
    
    function clearRenterTemplate(template_id, data, location_id){
        $(location_id).html('');
        renderTemplate(template_id, data, location_id);
    }
    
    function getTimetableData(){
        return ajax.jsonRpc('/json_get_timetable_params', 'call', {
            semester: $('#semester-select option:selected').attr('data-semester-id'),
            parameter: $('#parameter-select option:selected').attr('data-parameter')
        }).then(function(response){
            if (response) {
                clearRenterTemplate('minerva.options', response, '#groups-list');
            }
        });
    }

    $('#semester-select, #parameter-select').on('change', function(){
        clearRenterTemplate('minerva.options', false, '#groups-list');
        clearRenterTemplate('minerva.timetable_group', false, '#timetable');
        getTimetableData();
    });
    
    function getParamTimetableData(){
        return ajax.jsonRpc('/json_get_timetable_data', 'call', {
            semester2: $('#semester-select option:selected').attr('data-semester-id'),
            parameter2: $('#parameter-select option:selected').attr('data-parameter'),
            timetable2: $('#groups-list option:selected').attr('data-groups-id')
            
        }).then(function(response){
            if (response) {
                clearRenterTemplate('minerva.timetable_group', response, '#timetable');
            }
        });
    }
    
    $('#groups-list').on('change', function(){
        clearRenterTemplate('minerva.timetable_group', false, '#timetable');
        getParamTimetableData();
    });
    
    function getExamtableData(){
        return ajax.jsonRpc('/json_get_examtable_params', 'call', {
            semester: $('#exam-semester-select option:selected').attr('data-semester-id'),
            parameter: $('#exam-parameter-select option:selected').attr('data-parameter')
        }).then(function(response){
            if (response) {
                clearRenterTemplate('minerva.exam-options', response, '#exam-groups-list');
            }
        });
    }

    $('#exam-semester-select, #exam-parameter-select').on('change', function(){
        clearRenterTemplate('minerva.exam-options', null, '#exam-groups-list');
        clearRenterTemplate('minerva.examtable_group', null, '#examtable');
        getExamtableData();
    });
    
    function getParamExamtableData(){
        return ajax.jsonRpc('/json_get_examtable_data', 'call', {
            semester2: $('#exam-semester-select option:selected').attr('data-semester-id'),
            parameter2: $('#exam-parameter-select option:selected').attr('data-parameter'),
            timetable2: $('#exam-groups-list option:selected').attr('data-groups-id')
            
        }).then(function(response){
            if (response) {
                clearRenterTemplate('minerva.examtable_group', response, '#examtable');
            }
        });
    }
    
    $('#exam-groups-list').on('change', function(){
        clearRenterTemplate('minerva.examtable_group', null, '#examtable');
        getParamExamtableData();
    });
    
    
});