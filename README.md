# studentvue-reporter
 
A tool to help programmatically generate reports for students using the [StudentVue API](https://github.com/StudentVue/StudentVue.py).

A `credentials.json` file is required. Format:
```json
{
    "<student_name>": {
            "username": "<username>",
            "password": "<password>",
            "domain": "<domain>"
    }
}
```

SendGrid (optional) is used to email the reports. A `sendgrid.env` file is also recommended. It should contain:
```
export SENDGRID_API_KEY=<api_key>
export SENDGRID_FROM_EMAIL=<from_email>
export SENDGRID_TO_EMAILS=<to_email>
```
When running locally, run `source ./sendgrid.env` to load the envrionment variables.