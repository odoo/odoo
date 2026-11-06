
hols = env['university.holiday'].search([])
print('University Holidays:')
for h in hols:
    print(f'   {h.name}: {h.date_start} to {h.date_end}')

pub_hols = env['school.public.holiday'].search([])
print('Public Holidays:')
for h in pub_hols:
    print(f'   {h.name}: {h.date_from} to {h.date_to}')
