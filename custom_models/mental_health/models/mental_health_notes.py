from odoo import fields, models


class MentalHealthNotes(models.Model):
    _name = "mental_health.notes"
    _description = "A model to be used to write mental health notes"

    name = fields.Char(string='Client Name', required=True)
    description = fields.Text(string='Meeting Notes', copy=False)
    date = fields.Date(string='Date Recorded', required=True, default=lambda self: fields.Date.today(), copy=False)
    icd10_codes = fields.Selection(string='ICD10 Code', required=False, copy=False,
                                   selection=[('f40.00', 'F40.00 - Agoraphobia unspecified'),
                                              ('f40.01', 'F40.01 - Agoraphobia with panic disorder')])
    thought_process = fields.Selection(string='Thought Process', copy=False,
                                       selection=[('normal', 'Normal'),
                                                  ('lessened awareness', 'Lessened awareness'),
                                                  ('memory deficiency', 'Memory deficiency'),
                                                  ('disoriented', 'Disoriented'),
                                                  ('disorganized', 'Disorganized'),
                                                  ('vigilant', 'Vigilant'),
                                                  ('delusional', 'Delusional'),
                                                  ('hallucinating', 'Hallucinating')],
                                       help='Select the thought process of the client.')
    suicidal_homicidal = fields.Selection(string='Suicidal/Homicidal', copy=False,
                                          selection=[('none', 'None'),
                                                     ('ideation only', 'Ideation only'),
                                                     ('threat', 'Threat'),
                                                     ('gesture', 'Gesture'),
                                                     ('rehearsal', 'Rehearsal'),
                                                     ('attempt', 'Attempt'),
                                                     ('plan', 'Plan')],
                                          help='Is the client suicidal or homicidal?')
    insight = fields.Selection(string='Insight', copy=False,
                               selection=[('poor', 'Poor'),
                                          ('limited', 'Limited'),
                                          ('fair', 'Fair'),
                                          ('good', 'Good')],
                               help='Select the level of insight of the client.')
    participation = fields.Selection(string='Participation Level', copy=False,
                                     selection=[('active', 'Active'),
                                                ('variable', 'Variable'),
                                                ('responsive only', 'Responsive only'),
                                                ('minimal', 'Minimal'),
                                                ('resistant', 'Resistant')],
                                     help='Select the participation level of the client.')
    motivation = fields.Selection(string='Motivation', copy=False,
                                  selection=[('low', 'Low'),
                                             ('moderate', 'Moderate'),
                                             ('high', 'High')],
                                  help='Select the level of motivation of the client.')
    affect = fields.Selection(string='Affect', copy=False,
                              selection=[('normal', 'Normal'),
                                         ('slumped', 'Slumped'),
                                         ('slowed', 'Slowed'),
                                         ('confident', 'Confident'),
                                         ('energetic', 'Energetic'),
                                         ('nervous', 'Nervous'),
                                         ('fidgety', 'Fidgety')],
                              help='Select the affect of the client')
    symptom_change = fields.Selection(string='Change in Symptom Severity', copy=False,
                                      selection=[('resolved', 'Resolved'),
                                                 ('much improved', 'Much improved'),
                                                 ('less but still observable', 'Less but still observable.'),
                                                 ('same', 'Same'),
                                                 ('more severe', 'More severe')],
                                      help='Has there been any change in the symptom severity of the client?')
    diagnosis_selection = fields.Selection(string='Diagnosis', copy=False,
                                           selection=[('no change', 'No change'),
                                                      ('change', 'Change'),
                                                      ('additional', 'Additional')],
                                           help='Has there been a change in the diagnosis of the client?')
    judgment = fields.Selection(string='Judgment', copy=False,
                                selection=[('poor', 'Poor'),
                                           ('limited', 'Limited'),
                                           ('fair', 'Fair'),
                                           ('good', 'Good')],
                                help='Select the judgment level of the client.')
    eating = fields.Selection(string='Eating', copy=False,
                              selection=[('normal', 'Normal'),
                                         ('more', 'More'),
                                         ('binging', 'Binging'),
                                         ('less', 'Less'),
                                         ('starving', 'Starving'),
                                         ('over exercising', 'Over exercising')],
                              help='Select the eating patterns of the client.')
    sleep_quality = fields.Selection(string='Sleep Quality', copy=False,
                                     selection=[('normal', 'Normal'),
                                                ('restless/broken', 'Restless/broken'),
                                                ('insomnia', 'Insomnia'),
                                                ('nightmares', 'Nightmares'),
                                                ('oversleeps', 'Oversleeps')],
                                     help='Select the sleep quality of the client.')
    mood = fields.Selection(string='Mood', copy=False,
                            selection=[('normal', 'Normal'),
                                       ('anxious', 'Anxious'),
                                       ('depressed', 'Depressed'),
                                       ('angry', 'Angry'),
                                       ('euphoric', 'Euphoric')],
                            help='Select the mood of the client.')
