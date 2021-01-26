import json
from studentvue import StudentVue

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
        course['@Title']:{
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
                    for assignment in mark['Assignments'].get('Assignment', [])
                ]
            }
            for mark in course['Marks']['Mark']
        }
        for course in gradebook['Gradebook']['Courses']['Course']
    }
    return courses

def parse_score(score: str, score_type: str, points: str) -> str:
    if score == 'Not Graded':
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
                assignment_name = assignment['Name']
                if len(assignment_name) > assignment_name_width:
                    assignment_name = assignment_name[:(assignment_name_width - 3)] + '...'
                score = parse_score(assignment['Score'], assignment['Score Type'], assignment['Points'])
                report += assignment_name.ljust(assignment_name_width) + separator_string + assignment['Due Date'].ljust(due_date_width) + \
                          separator_string + score.rjust(score_width) + '\n'

    with open(f'{name}.report.txt', 'w') as file:
        file.write(report)
    
    return report

def main():
    credentials = load_credentials()
    students = list(credentials.keys())
    print(students)
    student = credentials[students[0]]
    print(student)
    sv = StudentVue(student['username'], student['password'], student['domain'])
    gradebook = json.loads(json.dumps(sv.get_gradebook()))
    print(generate_full_report(students[0], clean_grades(gradebook), True))

if __name__ == "__main__":
    main()