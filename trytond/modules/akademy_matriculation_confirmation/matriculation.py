# This file is part of SAGE Education.   The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields, ModelView
from trytond.wizard import Button, StateTransition, StateView, Wizard
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Not
from trytond.exceptions import UserError

from ..akademy_classe.classe import ClasseStudentDiscipline
from ..akademy_classe.variables import _MATRICULATION_STATE


class MatriculationCreateWzardStart(metaclass=PoolMeta):
    'Matriculation CreateStart'
    __name__ = 'akademy_matriculation.wizmatriculation.create.start'

    is_candidate = fields.Boolean(
        'Candidate', 
        states={
            'invisible':  Bool(Eval('is_transferred')) | Bool(Eval('is_student'))
        }, depends=['is_transferred', 'is_student'], 
        help="Registration for candidates.")
    is_transferred = fields.Boolean(
        'Transferred', 
        states={
            'invisible':  Bool(Eval('is_candidate')) | Bool(Eval('is_student'))
        }, depends=['is_candidate', 'is_student'], 
        help="Registration for a transferred student.")
    is_student = fields.Boolean(
        'Is Student', 
        states={
            'invisible':  Bool(Eval('is_candidate')) | Bool(Eval('is_transferred'))
        }, depends=['is_candidate', 'is_transferred'], 
        help="Confirmation of student enrollment.")
    student = fields.Many2One(
        'company.student', 'Student',
        states={
            'invisible': Not(Bool(Eval('is_student'))), 
            'required': Bool(Eval('is_student'))
        }, help="The student will be enrolled.")
    classes = fields.Many2One(
        'akademy_classe.classes', 'Class',
        states={
            'invisible': Not(Bool(Eval('is_student'))), 
            'required': Bool(Eval('is_student'))
        }, help="Enter the name of the class.")


class MatriculationCreateWzard(metaclass=PoolMeta):
    'Matriculation CreateWzard'
    __name__ = 'akademy_matriculation.wizmatriculation.create'

    start_state = 'start'
    start = StateView(
        'akademy_matriculation.wizmatriculation.create.start', 
        "akademy_matriculation_confirmation.act_matriculation_wizard_from", [
            Button(string=u'Cancel', state='end', icon='tryton-cancel'),
            Button(string=u'Enroll', state='matriculation', icon='tryton-save')
        ]
    )
    matriculation = StateTransition()

    def transition_matriculation(self):
        if (self.start.is_candidate == True):
            self.student_candidate(self.start.applications.application)
        if (self.start.is_transferred == True):
            self.student_transferred(self.start.transferred)
        if (self.start.is_student == True):
            MatriculationCreateWzard.matriculation_confirmation(self.start.student, self.start.classes)
                    
        return 'end'

    @classmethod
    def matriculation_confirmation(cls, company_student, classes, exception=True):
        student_new_matriculation = []
        ClasseStudent = Pool().get('akademy_classe.classe.student')
        Student_Discipline = Pool().get('akademy_classe.classe.student.discipline')
        CourseYear = Pool().get('akademy_configuration.course.classe')  

        student_has_matriculation = ClasseStudent.search([('student', '=', company_student)])
        classes_course_year = CourseYear.search([
            ('classe', '=', classes.classe), 
            ('course', '=', classes.studyplan.course)
            ], limit=1)
        confirmation = True
        student_approved = 0
        student_state = ['approved', 'suspended', 'cancelled', 'transferred', 'failed']

        if len(student_has_matriculation) > 0:
            classe_student = student_has_matriculation[len(student_has_matriculation) -1]
            course_years = CourseYear.search([ 
                ('course', '=', classe_student.classes.studyplan.course)
                ]) 
            student_course_year = int(course_years[len(course_years)-1].course_year)
            verify_year =  student_course_year - int(classes_course_year[0].course_year)
                                               
            for student in student_has_matriculation:

                NoneType = type(None)
                if type(student.student.state) == NoneType:
                    raise UserError("We were unable to proceed with enrollment. Please complete the optional fields on "+
                                    "the student form to continue with enrollment confirmation.") 
                
                if student.state not in student_state:  
                    student_matriculation = ClasseStudent.search([
                        ('student', '=', student.student), 
                        ('classes', '=', classes)
                        ], limit=1)                      
                    confirmation = True
                      
                    if classes == student.classes:
                        raise UserError("The student "+company_student.party.name+", cannot attend class "+classes.classe.name+
                                ", in the class "+classes.name+", because he is already enrolled in that class.")
                    else:
                        if classes > student.classes:                           
                            if len(student_matriculation) == 0:
                                MatriculationCreateWzard.matriculation_student_classe(
                                    ClasseStudent, 
                                    company_student, 
                                    classes, 
                                    Student_Discipline)                                 
                            else:        
                                if verify_year == 0:  
                                    if student.state in ['enrolled', 'approved']:
                                        pass
                                    if student.state.name == 'failed':                                        
                                        pass
                                    
                                elif verify_year == 1:              
                                    if student.state.name == 'approved':
                                        if student_approved == 0:
                                            MatriculationCreateWzard.matriculation_student_classe(
                                                ClasseStudent, 
                                                company_student, 
                                                classes, 
                                                Student_Discipline) 
                                            student_approved += 1
                                        else:
                                            pass
                                    if student.state.name == 'failed':                                        
                                        confirmation = False
                                                   
                                else:
                                    raise UserError("The student could not be enrolled. "+company_student.party.name+
                                                    ", in the class "+classes.classe.name+", please check the status of the previous board.")
                                                                          
                        else:                            
                            confirmation = False
                else:
                    raise UserError("The student "+company_student.party.name+", cannot attend class "+classes.classe.name+
                                    ", in the class "+classes.name+", please check the status of the previous board.")

            if confirmation == False:
                raise UserError("The student "+company_student.party.name+", cannot attend class "+classes.classe.name+
                                ", because he/she failed the class "+company_student.classe.name)

        else:
            course_frist_year = 1
            verify_year = course_frist_year - int(classes_course_year[0].course_year)
            
            if verify_year == 0:
                if company_student.state not in student_state: 
                    MatriculationCreateWzard.matriculation_student_classe(
                        ClasseStudent, 
                        company_student, 
                        classes, 
                        Student_Discipline)                 
            else:
                raise UserError("The student could not be enrolled. "+company_student.party.name+
                                ", in the class "+classes.classe.name+", please check the student's situation.")

    @classmethod
    def matriculation_student_classe(cls, ClasseStudent, company_student, classes, ClasseStudentDiscipline):
        DisciplineModality = Pool().get('akademy_configuration.discipline.modality')
        matriculation_state = 'enrolled'
        matriculation_type = 'class_transition'
        
        classe_has_student = ClasseStudent.search([
            ('student', '=', company_student), ('classes', '=', classes)
            ])
            
        if len(classe_has_student) == 0:
            MatriculationStudent = ClasseStudent.save_student_matriculation(
                matriculation_state, 
                matriculation_type, 
                company_student, classes)        
        
            for studyplan_discipline in classes.studyplan.studyplan_discipline:
                student_matriculation = ClasseStudentDiscipline.search([
                    ('classe_student', '=', MatriculationStudent), 
                    ('studyplan_discipline', '=', studyplan_discipline)
                    ])
                
                if len(student_matriculation) > 0:
                    pass
                else:
                    matriculation_state = 'enrolled'
                    discipline_modality = 'in_person'
                    
                    if len(studyplan_discipline.discipline_precedentes) > 0:                    
                        ClasseStudentDiscipline.save_student_discipline(
                            MatriculationStudent, studyplan_discipline, matriculation_state[0], discipline_modality[0])                                        
                    else:      
                        ClasseStudentDiscipline.save_student_discipline(
                            MatriculationStudent, studyplan_discipline, matriculation_state[0], discipline_modality[0])
       

class ChangeMatriculationCreateWizardStart(ModelView):
    "ChangeMatriculation CreateStart"
    __name__ = 'akademy_matriculation_confirmation.wizchangematriculation.create.start'
    
    classe_student = fields.Many2One(
        'akademy_classe.classe.student', 'Student',
        required=True,
        help="Choose the student.")  
    classes = fields.Many2One(
        'akademy_classe.classes', 'Class',
        required=True,
        help="Choose the class where the change will be made.")


class ChangeMatriculationChangeCreateWizard(Wizard):
    "ChangeMatriculation CreateWizard"
    __name__ = 'akademy_matriculation_confirmation.wizchangematriculation.create'

    start_state = 'start'
    start = StateView(
        'akademy_matriculation_confirmation.wizchangematriculation.create.start', 
        "akademy_matriculation_confirmation.act_changematriculation_wizard_from", [
            Button(string=u'Cancel', state='end', icon='tryton-cancel'),
            Button(string=u'Change', state='changematriculation', icon='tryton-save')
        ]
    )
    changematriculation = StateTransition()

    def transition_changematriculation(self): 

        if self.start.classe_student.classes.state == False: 
            if self.start.classe_student.state in ['enrolled']:
                if self.start.classe_student.classes != self.start.classes and self.start.classe_student.classes.classe == self.start.classes.classe:
                    if self.start.classe_student.classes.studyplan.course == self.start.classes.studyplan.course:
                        
                        matriculation_state = 'change_registration'
                        self.start.classe_student.state = matriculation_state #[0]
                        self.start.classe_student.save()

                        for classe_student_discipline in self.start.classe_student.classe_student_discipline:
                            classe_student_discipline.state = matriculation_state
                            classe_student_discipline.save()

                        ClasseStudent = Pool().get('akademy_classe.classe.student')
                        max_student = self.start.classes.max_student + 1
                        
                        if self.start.classes.max_student < max_student:
                            matriculation_state = 'enrolled'
                            matriculation_type = 'change_of_class'
                            
                            MatriculationStudent = ClasseStudent(
                                state = matriculation_state,
                                type = matriculation_type,
                                student = self.start.classe_student.student,
                                classes = self.start.classes,
                            )
                            MatriculationStudent.save()
                                            
                        for studyplan_discipline in self.start.classes.studyplan.studyplan_discipline:
                            discipline_modality = 'in_person'
                            matriculation_state = 'enrolled'
                                                    
                            ClasseStudentDiscipline.save_student_discipline(
                                MatriculationStudent, studyplan_discipline, 
                                matriculation_state, discipline_modality)
                            
                    else:            
                        raise UserError("It was not possible to proceed with the class change because the courses are different.")
                else:       
                    raise UserError("It was not possible to proceed with the class change because the classes are the "+
                                    "same or from different grade levels.")                                    
            else:      
                raise UserError("We were unable to proceed with the class change; please check your enrollment status.")
            
        else:
            raise UserError("It is not possible to enroll the student or candidate because the class is already full.")

        return 'end'
