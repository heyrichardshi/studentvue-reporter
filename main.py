import json
import os
from datetime import datetime, timedelta, date
from studentvue import StudentVue
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def load_credentials(filename: str = 'credentials.json') -> dict:
    with open('credentials.json', 'r') as f:
        credentials = json.load(f)
        return credentials

def clean_grades(gradebook: dict) -> dict:
    reporting_periods = gradebook['Gradebook']['ReportingPeriods']['ReportPeriod']
    # reporting_periods is a list of dicts with keys '@Index', '@GradePeriod', '@StartDate', '@EndDate'

    current_reporting_period = gradebook['Gradebook']['ReportingPeriod']
    # current_reporting_period is a dict with same keys as reporting_periods sans `@Index`

    courses = {
        course['@Title']: {
            mark['@MarkName']: {
                'Overall Grade': mark['@CalculatedScoreString'],
                'Raw Grade': mark['@CalculatedScoreRaw'],
                'Assignments': [
                    {
                        'Name': assignment['@Measure'],
                        'Date': assignment['@Date'],
                        'Due Date': assignment['@DueDate'],
                        'Score': assignment['@Score'],
                        'Score Type': assignment['@ScoreType'],  # possible values: 'Percentage', 'Raw Score'
                        'Points': assignment['@Points']
                    }
                    for assignment in (mark['Assignments'].get('Assignment', [])
                                       if isinstance(mark['Assignments'].get('Assignment', []), list)
                                       else [mark['Assignments'].get('Assignment')])
                ]
            }
            for mark in (course['Marks']['Mark']
                         if isinstance(course['Marks']['Mark'], list)
                         else [course['Marks']['Mark']])
        } if course['Marks'].get('Mark') else {}
        for course in gradebook['Gradebook']['Courses']['Course']
    }
    return courses

def parse_score(score: str, score_type: str, points: str) -> str:
    if score in ['Not Graded', 'Not Due']:
        return score
    if score_type == 'Percentage':
        return f'{float(score):.2f}'
    if score_type == 'Raw Score':
        split_score = score.split(' out of ')
        if len(split_score) == 2:
            num, den = split_score
            return f'{float(num) / float(den) * 100:.2f}'
    split_points = points.split(' / ')
    if len(split_points) == 2:
        num, den = split_points
        return f'{float(num) / float(den) * 100:.2f}'
    return score + '?'

def generate_full_report(name: str, courses: dict, write: bool = False) -> str:
    report_width = 120
    separator_width = 2
    due_date_width = 10
    score_width = 20
    assignment_name_width = report_width - 2 * separator_width - due_date_width - score_width
    separator_string = separator_width * ' '

    report = name.ljust(report_width, '_') + '\n'
    for course, markings in courses.items():
        report += '\n<*> ' + course.upper() + '\n'
        report += 'Assignment'.ljust(assignment_name_width) + separator_string + \
                  'Due Date'.ljust(due_date_width) + separator_string + 'Score'.rjust(score_width) + '\n'
        for mark_name, marking in markings.items():
            report += mark_name.ljust(report_width - score_width, '>') + \
                      f'{marking["Overall Grade"]} ({marking["Raw Grade"]})'.rjust(score_width, '>') + '\n'
            for assignment in marking['Assignments']:
                assignment_name = str(assignment['Name'])
                if len(str(assignment_name)) > assignment_name_width:
                    assignment_name = assignment_name[:(assignment_name_width - 3)] + '...'
                score = parse_score(assignment['Score'], assignment['Score Type'], assignment['Points'])
                report += assignment_name.ljust(assignment_name_width) + separator_string + assignment['Due Date'].ljust(due_date_width) + \
                          separator_string + score.rjust(score_width) + '\n'

    with open(f'reports/{name}.report.txt', 'w') as file:
        file.write(report)

    return report

def generate_partial_report(name: str, courses: dict, lookback: int, write: bool = False) -> str:
    report_width = 120
    separator_width = 2
    due_date_width = 10
    score_width = 20
    assignment_name_width = report_width - 2 * separator_width - due_date_width - score_width
    separator_string = separator_width * ' '

    anchor_date = date.today() - timedelta(days=lookback)

    report = name.ljust(report_width, '_') + '\n'
    for course, markings in courses.items():
        report += '\n<*> ' + course.upper() + '\n'
        report += 'Assignment'.ljust(assignment_name_width) + separator_string + \
                  'Due Date'.ljust(due_date_width) + separator_string + 'Score'.rjust(score_width) + '\n'
        for mark_name, marking in markings.items():
            report += mark_name.ljust(report_width - score_width, '>') + \
                      f'{marking["Overall Grade"]} ({marking["Raw Grade"]})'.rjust(score_width, '>') + '\n'
            for assignment in marking['Assignments']:
                due_date = assignment['Due Date']
                dd_month, dd_day, dd_year = due_date.split('/')
                if date(int(dd_year), int(dd_month), int(dd_day)) > anchor_date:
                    assignment_name = str(assignment['Name'])
                    if len(assignment_name) > assignment_name_width:
                        assignment_name = assignment_name[:(assignment_name_width - 3)] + '...'
                    score = parse_score(assignment['Score'], assignment['Score Type'], assignment['Points'])
                    report += assignment_name.ljust(assignment_name_width) + separator_string + due_date.ljust(due_date_width) + \
                              separator_string + score.rjust(score_width) + '\n'

    with open(f'reports/{name}.partial.report.txt', 'w') as file:
        file.write(report)

    return report

def send_email(report: str, subject: str):
    from_email = os.environ.get('SENDGRID_FROM_EMAIL')
    to_emails = os.environ.get('SENDGRID_TO_EMAILS')
    report = report.replace('\n', '<br>')
    report = report.replace(' ', '&nbsp;')

    if not (from_email and to_emails):
        print('Invalid from or to email(s).')
        return

    message = Mail(
        from_email=from_email,
        to_emails=to_emails,
        subject=subject,
        html_content=f'<div style="width:865px"><code style="width:100%">{report}</code></div>')
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)

def main():
    for student, credentials in load_credentials().items():
        sv = StudentVue(credentials['username'], credentials['password'], credentials['domain'])
        gradebook = json.loads(json.dumps(sv.get_gradebook()))
        # TODO: implement option to view specific marking period
        # with open(f'reports/{student}.gradebook.report.txt', 'w') as file:
        #     file.write(json.dumps(gradebook))
        grades = clean_grades(gradebook)
        partial_report = generate_partial_report(student, grades, 14, True)
        # generate_full_report(student, grades, True)
        # send_email(partial_report, student + ' - Grade Report (Past 2 Weeks)')

if __name__ == "__main__":
    main()