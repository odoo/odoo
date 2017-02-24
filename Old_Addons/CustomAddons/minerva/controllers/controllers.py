# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request
from pychart.tick_mark import Null
#from openerp.addons.web import http
#from openerp.addons.web.http import request

class Minerva(http.Controller):
    
    @http.route('/paskaitos', auth='public' , website= True)
    def timetable_index(self, **kw):
        semestrai = http.request.env['op.xsemester']
        #badges = sorted(paskaitos, key=lambda b: op.timetable, reverse=True)
        return http.request.render('minerva.main', {
            'semestrai':semestrai.search([('active' ,'=',True)]),

           
            })
        
    @http.route('/json_get_timetable_params', type='json', auth='public' , website= True)
    def timetable_params(self, **post):
        print post
        parameter = post.get('parameter')
        print parameter
        if parameter == 'Studento':
            print request.env['op.batch'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])
            return {'groups': request.env['op.batch'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])}
        if parameter == 'Destytojo':
            print request.env['op.faculty'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])
            return {'faculties': request.env['op.faculty'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])}
        
        if parameter == 'Dalyko':
            data = request.env['op.subject'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])
            print data
            data= sorted(data, key=lambda b: 'id', reverse= True)
            print data
            return {'subjects': request.env['op.subject'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])}

        if parameter ==  'Auditorijos':
            print request.env['op.classroom'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])
            return {'classrooms': request.env['op.classroom'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])}
        
        if parameter ==  'Dienos':
            days=  [('1', 'Pirmadienis'), ('2', 'Antradienis'),
            ('3', 'Trečiadienis'), ('4', 'Ketvirtadienis'),
            ('5', 'Penktadienis'), ('6', 'Šeštadienis')]
            print days
            return {'days' :days}
        #  return {'days': request.env['op.d'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])}
        
        
    @http.route('/json_get_timetable_data', type='json', auth='public' , website= True)
    def generate_timetable(self, **post):
        print '/json_get_timetable_data', post
        parameter= post.get('parameter2')
        timetable = int(post.get('timetable2').split(',')[-1])
        domain = [('active', '=', True)]
        semester = int(post.get('semester2'))
        domain.append(('xsemester_id','=',semester))
        if parameter == 'Studento':
            domain.append(('batch_id','=',timetable))
        elif parameter =='Destytojo':
            domain.append(('faculty_id','=',timetable))
        elif parameter == 'Dalyko':
            domain.append(('subject_id','=',timetable)) 
        elif parameter ==  'Auditorijos':
            domain.append(('classroom_id','=',timetable))
        elif parameter == 'Dienos':
            domain.append(('day','=',post.get('timetable2')))
        else:
            return {}
        
        data= request.env['op.timetable'].sudo().search_read(domain,fields=['id', 'xsemester_id']) 
        domain1 = domain
        domain1.append(('day','=','1'))
        data1= request.env['op.timetable'].sudo().search_read(domain1,fields=['id', 'faculty_id' , 'batch_id','subject_id' , 'period_id', 'classroom_id' , 'week' , 'note', 'xsemester_id']) 
        if data1 == []:
            data1=None
       
        domain2 = list(domain)
        domain2.pop()
        domain2.append(('day','=','2'))
        domain2= tuple(domain2)
        data2= request.env['op.timetable'].sudo().search_read(domain2,fields=['id', 'faculty_id' , 'batch_id','subject_id' , 'period_id', 'classroom_id' , 'week' , 'note', 'xsemester_id']) 
        if data2 == []:
            data2=None
            
        domain3 = list(domain)
        domain3.pop()
        domain3.append(('day','=','3'))
        domain3= tuple(domain3)
        data3= request.env['op.timetable'].sudo().search_read(domain3,fields=['id', 'faculty_id' , 'batch_id','subject_id' , 'period_id', 'classroom_id' , 'week' , 'note', 'xsemester_id'])
        if data3 == []:
            data3=None
            
        domain4 = list(domain)
        domain4.pop()
        domain4.append(('day','=','4'))
        domain4= tuple(domain4)
        data4= request.env['op.timetable'].sudo().search_read(domain4,fields=['id', 'faculty_id' , 'batch_id','subject_id'  , 'period_id', 'classroom_id' , 'week' , 'note', 'xsemester_id'])
        if data4 == []:
            data4=None
            
        domain5 = list(domain)
        domain5.pop()
        domain5.append(('day','=','5'))
        domain5= tuple(domain5)
        data5= request.env['op.timetable'].sudo().search_read(domain5,fields=['id', 'faculty_id' , 'batch_id','subject_id'  , 'period_id', 'classroom_id' , 'week' , 'note', 'xsemester_id'])
        if data5 == []:
            data5=None
       
        domain6 = list(domain)
        domain6.pop()
        domain6.append(('day','=','6'))
        domain6= tuple(domain6)
        data6= request.env['op.timetable'].sudo().search_read(domain6,fields=['id', 'faculty_id' , 'batch_id','subject_id', 'period_id', 'classroom_id' , 'week' , 'note', 'xsemester_id'])
        if data6 == []:
            data6=None
            
        if data != []:
            if (parameter) and (timetable) and [data]:
                return {'timetables': data,
                        'pirmadienis': data1,
                        'antradienis': data2,
                        'treciadienis': data3,
                        'ketvirtadienis' : data4,
                        'penktadienis': data5,
                        'sestadienis': data6
                        }
        else: return {}
            

        
###### Egzaminai    
    @http.route('/egzaminai', auth='public' , website= True)
    def exam_index(self, **kw):
        semestrai = http.request.env['op.xsemester']
        return http.request.render('minerva.exam_index',{'semestrai':semestrai.search([ ('active' ,'=',True)]) })
        
    @http.route('/json_get_examtable_params', type='json', auth='public' , website= True)
    def examtable_params(self, **post):
        print post
        parameter = post.get('parameter')
        print parameter
        if parameter == 'Studento':
            print request.env['op.batch'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])
            return {'groups': request.env['op.batch'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])}
        if parameter == 'Destytojo':
            print request.env['op.faculty'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])
            return {'faculties': request.env['op.faculty'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])}
        
        if parameter == 'Dalyko':
            print request.env['op.subject'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])
            return {'subjects': request.env['op.subject'].sudo().search_read([('active', '=', True)], fields=['id', 'name'])}

        if parameter ==  'Auditorijos':
            print request.env['op.classroom'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])
            return {'classrooms': request.env['op.classroom'].sudo().search_read([('active', '=', True)], fields=['id', 'code'])}
        
        
    @http.route('/json_get_examtable_data', type='json', auth='public' , website= True)
    def generate_examtable(self, **post):
        print '/json_get_examtable_data', post
        parameter= post.get('parameter2')
        semester = int(post.get('semester2'))
        print 'Semestras'
        print semester
        timetable = int(post.get('timetable2').split(',')[-1])
        domain = [('active', '=', True)]
        domain.append(('xsemester_id','=',semester))
        if parameter == 'Studento':
            domain.append(('batch_id','=',timetable))
        elif parameter =='Destytojo':
            domain.append(('faculty_id','=',timetable))
        elif parameter == 'Dalyko':
            domain.append(('subject_id','=',timetable)) 
        elif parameter ==  'Auditorijos':
            domain.append(('classroom_id','=',timetable))
        else:
            return {}
        
        #data = sorted(data, key=lambda k: k['']['update_time'], reverse=True)
        if (parameter) and (timetable):
                examdata= request.env['op.exam'].sudo().search_read(domain,fields=['id', 'faculty_id' , 'batch_id','subject_id', 'classroom_id', 'notes', 'start_date','exam_time_name']) 
                if examdata == []:
                    examdata=None
                return {'examtables': examdata}
#     def list(self, **kw):
#         return http.request.render('minerva.listing', {
#             'root': '/minerva/minerva',
#             'objects': http.request.env['minerva.minerva'].search([]),
#         })

#     @http.route('/minerva/minerva/objects/<model("minerva.minerva"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('minerva.object', {
#             'object': obj
#         })