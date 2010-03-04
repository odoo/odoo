import pooler
import datetime

def timeformat_convert(cr, uid, time_string, context={}):
#    Function to convert input time string:: 8.5 to output time string 8:30

        split_list = str(time_string).split('.')
        hour_part = split_list[0]
        mins_part = split_list[1]
        round_mins  = int(round(float(mins_part) * 60,-2))
        converted_string = hour_part + ':' + str(round_mins)[0:2]
        return converted_string

def leaves_resource(cr, uid, calendar_id, resource_id=False, resource_calendar=False):
#    To get the leaves for the resource_ids working on phase

        pool = pooler.get_pool(cr.dbname)
        resource_leaves_pool = pool.get('resource.calendar.leaves')
        leaves = []
        if resource_id:
            resource_leave_ids = resource_leaves_pool.search(cr, uid, ['|', ('calendar_id','=',calendar_id), ('calendar_id','=',resource_calendar), ('resource_id','=',resource_id)])
        else:
            resource_leave_ids = resource_leaves_pool.search(cr, uid, [('calendar_id','=',calendar_id), ('resource_id','=',False)])
        res_leaves = resource_leaves_pool.read(cr, uid, resource_leave_ids, ['date_from', 'date_to'])
        for leave in range(len(res_leaves)):
                dt_start = datetime.datetime.strptime(res_leaves[leave]['date_from'], '%Y-%m-%d %H:%M:%S')
                dt_end = datetime.datetime.strptime(res_leaves[leave]['date_to'], '%Y-%m-%d %H:%M:%S')
                no = dt_end - dt_start
                [leaves.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
                leaves.sort()
        return leaves

def compute_working_calendar(cr, uid, calendar_id):
#     To change the format of working calendar to bring it into 'faces' format

        pool = pooler.get_pool(cr.dbname)
        resource_week_pool = pool.get('resource.calendar.week')
        time_range = "8:00-8:00"
        non_working = ""
        wk = {"0":"mon","1":"tue","2":"wed","3":"thu","4":"fri","5":"sat","6":"sun"}
        wk_days = {}
        wk_time = {}
        wktime_list = []
        wktime_cal = []
        week_ids = resource_week_pool.search(cr, uid, [('calendar_id','=',calendar_id)])
        week_obj = resource_week_pool.read(cr, uid, week_ids, ['dayofweek', 'hour_from', 'hour_to'])

#     Converting time formats into appropriate format required
#     and creating a list like [('mon', '8:00-12:00'), ('mon', '13:00-18:00')]
        for week in week_obj:
            res_str = ""
            if wk.has_key(week['dayofweek']):
                day = wk[week['dayofweek']]
                wk_days[week['dayofweek']] = wk[week['dayofweek']]

            hour_from_str = timeformat_convert(cr, uid, week['hour_from'])
            hour_to_str = timeformat_convert(cr, uid, week['hour_to'])
            res_str = hour_from_str + '-' + hour_to_str
            wktime_list.append((day, res_str))

#     Converting it to format like [('mon', '8:00-12:00', '13:00-18:00')]
        for item in wktime_list:
            if wk_time.has_key(item[0]):
                wk_time[item[0]].append(item[1])
            else:
                wk_time[item[0]] = [item[0]]
                wk_time[item[0]].append(item[1])

        for k,v in wk_time.items():
            wktime_cal.append(tuple(v))

#     For non working days adding [('tue,wed,fri,sat,sun', '8:00-8:00')]
        for k,v in wk_days.items():
            if wk.has_key(k):
                wk.pop(k)
        for v in wk.itervalues():
            non_working += v + ','
        if non_working:
            wktime_cal.append((non_working[:-1], time_range))

        return wktime_cal