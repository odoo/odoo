totale_hours,points=0,0
pats_hours,past_rate,total_points=0,0,0
grades={'a+':4,'a':3.75,'b+':3.5,'b':3,'c+':2.5,'c':2,'d+':1.5,'d':1,'f':0,}
pats_hours=input('are you have a past hours ? if not choose 0 : ')
if int(pats_hours)>0:
    past_rate=input('what is your total rate ? ')
totale_course=input('what is your total courses ? ')
for x in range(int(totale_course)):
    hours_course=float(input('how many hours for the course ? '))
    grades_course=(input('what is your grade ? '))
    grades_course=(grades_course.lower())
    points_course=(grades[grades_course])
    points=float(points_course)*hours_course
    totale_hours+=hours_course
    total_points+=points
rate=total_points/totale_hours 
totale_hours_r=totale_hours+int(pats_hours)
total_rate=total_points+float(past_rate)*int(pats_hours)
print(totale_hours,pats_hours,total_points,past_rate,pats_hours)
totalt=total_rate/totale_hours_r
print('your total hours is :'+str(int(totale_hours+int(pats_hours)))+'\nyour rate is : '+str(round(rate,3))+'\nand you total rate is : '+str(round(totalt,3)))