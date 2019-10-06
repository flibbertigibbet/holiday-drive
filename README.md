## holiday-drive

Django website for running a holiday gift drive.

### Local development

Requirements:

 - python 2
 - `pip`
 - `virtualenv`

Set up virtual environment and install dependencies:

`virtualenv env --python=python2.7`
`source env/bin/activate`
`pip install -r requirements.txt`

Run migrations:

 - `cd holiday`
 - `./manage.py migrate`

Load test data from fixtures (to default `sqlite` database):

- `./manage.py loaddata initial_data` for test programs and wishlist items
-   `./manage.py loaddata states_data` for US states and abbreviations

Create a user by following the prompts:

 - `./manage.py createsuperuser`

Start development server:

 - `./manage.py rumserver`

Log in to the Django `admin` backend with the newly created user at: http://localhost:8000/admin.

Assign a program to the user. Uncheck "first login" to prevent it prompting to change password on the staff site.

Now the staff site can be accessed at http://localhost:8000/staff_start. Create some children and families.\

In the admin site, create a user group called 'Program Directors' and add at least one staff user to the group. Program directors can approve children entered by other staff. Once approved, the children show in the visitor-facing search results as available for sponsorship.

Alternatively, go to the `admin` site and mark children as "approved by program director" or use the "Keep selected children available" list action for them to show in the search results.

Now the children will show in the search results on the visitor-facing site: http://localhost:8000/

Now the local database should be set up with enough data to test the website.

The four parts of the website:

- The visitor-facing site: http://localhost:8000/
- The staff site: http://localhost:8000/staff_start
- The program director site (approves children entered by staff): http://localhost:8000/program_director_initial/
- The administrative site: http://localhost:8000/admin

To re-create the local sqlite database, delete the `holiday.db` file and re-run migrations to create it again. Alternatelhy, run the `./recreatedb.sh` script.

For running in production, be sure to run `./manage.py collectstatic` to copy static files.
