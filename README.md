simple web based grading system, for tracking and managing student grades and some functionalities

basic functionalities
- analytics for student grades and thier performance on both teacher and student's UI
- analytics for grades and overall performance of the section on the teachers side
- read time email notification system for when the student was registerd to the system,
  and when when the teacher publish the grades for everyone(students) to see
- ability for students to view thier own grades
- students would have nice UIs for both desktop and mobile
- teachers would need desktop to use to display more information at ones at the screen
  but that also makes the mobile experience compromized



prerequisite
- python3.12>=
- bash5.2.21>=

how to use:

first install python dependancies, its preferable to use venv
```console
$ cd <to/the/project/path>
$ python3 -m pip install requirements.txt
```
then run the bash script
you could create a service entry to turn the program as deamon
```console
$ ./run
```


- for administrator

only the admin could add students and teachers for now
and when admin adds a student, they should be notified that they're registered on the system


- for teachers, they can add categories, gradings and edit grades

- for students
the students will be given with thier own password and user name unique to them
then they can access thier grades
