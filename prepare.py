#!/usr/bin/python

import sys, os, re, glob, subprocess, pkgutil
import nbconvert, nbformat

# Dummy definitions to suppress errors in the notebook.
weight, name, description = [lambda x: lambda x: 0]*3

# Delimiter definitions.
start = "#!# BEGIN"
end = "#!# END"

usage_message = f"""Normal usage:
  Remove the SOLUTION and TESTS blocks from the solution notebook, and saves the result in the student notebook:

    $ python3 {sys.argv[0]} assignment [solution notebook].ipynb [student notebook].ipynb

  Remove the TESTS blocks from the solution notebook, and saves the result in the specified notebook.

    $ python3 {sys.argv[0]} remove-tests [solution notebook].ipynb [notebook without tests].ipynb

  Clears the output cells in the specified notebook:

    $ python3 {sys.argv[0]} clear-output [notebook].ipynb


Usage in the CodeGrade enviroment:
  Convert the solutions notebook to a .py file, to run the AutoTests:

    $ python3 {sys.argv[0]} solutions

  Convert the student hand-in notebook to a .py file, to run the AutoTests:

    $ python3 {sys.argv[0]} hand-in
"""


def remove_solutions(content, replace=r''):
    """
    Replaces all solution blocks from `content` with `replace`.

    Solution blocks in `content` are constructed as follows:
        #=# BEGIN SOLUTION
        ...
        #=# END SOLUTION
    """

    regex = rf'{start} SOLUTION(?!`)[\s\S]*?{end} SOLUTION'
    return re.sub(regex, replace, content)

def remove_tests(content, exclude=r'', replace=r''):
    """
    Replaces all test blocks from `content` with `replace`, except if their
    set category equals the `exclude` parameter.

    Test blocks in `content` are constructed as follows:
        #=# BEGIN [category name] TESTS
        ...
        #=# END [category name] TESTS

    Examples of categories are "VISIBLE", "HIDDEN", or user-defined categories.
    """

    regex = rf'{start} (?!{exclude} ).*?TESTS(?!`)[\s\S]*?{end} (?!{exclude} ).*?TESTS'
    return re.sub(regex, replace, content)


def tests(test_category=r''):
    """
    Run only in CodeGrade.
    In a Pytest step, write:

        import prepare
        exec(prepare.tests([test category]))

    """
    with open("solutions.py", 'r') as f:
        content = remove_tests(f.read(), test_category)

    return "import student\nfrom cg_pytest_reporter import weight, name, description\n" + content


def remove_output(notebook):
    """
    Removes the output cells of the specified notebook, given as a file path.
    """
    subprocess.run(f'jupyter nbconvert "{notebook}" --clear-output --inplace',
                   shell=True)

def remove_empty_cells(notebook):
    """
    Removes the cells containing only whitespace or newlines of the
    specified notebook, given as a file path.
    """
    with open(notebook, 'r') as f:
        content = nbformat.reads(f.read(), as_version=4)

    # Remove the empty cells
    pattern = re.compile(r'[\s\n]*\Z')
    content.cells = [cell for cell in content.cells if not pattern.match(cell.source)]

    with open(notebook, 'w') as f:
        f.write(nbformat.writes(content))


def remove_ipython_functions(py_file):
    """
    Removes Notebook/IPython specific functions from the given .py files, such as
    `display()` (replaced by `print`) and `ipython_get` (made into a comment).
    """
    # subprocess.run(f'sed -i "s/display/print/g" {py_file}', shell=True)
    subprocess.run(f'sed -i "s/get_ipython/#get_ipython/g" {py_file}', shell=True)

if __name__ == "__main__":
    # Check for correct input.
    if len(sys.argv) < 2 or (sys.argv[1] in ["assignment", "remove-tests"]
                             and len(sys.argv) < 4):
        print(usage_message)
        exit()

    # Check if the script is run in the CodeGrade enviroment.
    if sys.argv[1] in ["solutions", "hand-in"] and not "UPLOADED_FILES" in os.environ:
        print(usage_message)
        exit()


    if sys.argv[1] == "assignment":
        # Read the notebook.
        with open(sys.argv[2], 'r' ) as f:
            content = f.read()

        # Remove solutions and tests and write to file.
        with open(sys.argv[3], 'w') as f:
            content = remove_solutions(content, "#. Your solution here ...")
            content = remove_tests(content)
            f.write(content)

        remove_empty_cells(sys.argv[3])
        remove_output(sys.argv[3])

    elif sys.argv[1] == "solutions":
        uploaded_files = os.environ["UPLOADED_FILES"]
        # notebook = glob.glob(f"{uploaded_files}/*.ipynb")[0]

        # Rename the solution notebook.
        notebook = glob.glob(f"{uploaded_files}/*.ipynb")[0]
        os.rename(notebook, f"{uploaded_files}/solutions.ipynb")

        # Convert solutions notebook to a .py file.
        subprocess.run(f'jupyter nbconvert --to python {uploaded_files}/solutions.ipynb', shell=True)

        remove_ipython_functions(f"{uploaded_files}/solutions.py")

    elif sys.argv[1] == "hand-in":
        uploaded_files = os.environ["UPLOADED_FILES"]
        notebook = glob.glob("*.ipynb")[0]

        # Rename the student notebook and convert it to a .py file.
        os.rename(notebook, "student.ipynb")
        subprocess.run('jupyter nbconvert --to python student.ipynb', shell=True)

        remove_ipython_functions("student.py")

        # Remove any tests (from the test submission specifically).
        with open("student.py", 'r' ) as f:
            content = f.read()
        with open("student.py", 'w') as f:
            content = remove_tests(content)
            f.write(content)

        # Copy solutions and prepare files.
        os.rename(f'{uploaded_files}/solutions.py', 'solutions.py')
        os.rename(f'{uploaded_files}/prepare.py', 'prepare.py')

    elif sys.argv[1] == "remove-tests":
        # Read the notebook.
        with open(sys.argv[2], 'r' ) as f:
            content = f.read()

        # Remove solutions and tests and write to file.
        with open(sys.argv[3], 'w') as f:
            content = remove_tests(content)
            f.write(content)

        remove_empty_cells(sys.argv[3])

    elif sys.argv[1] == "clear-output":
        remove_output(sys.argv[2])

    else:
        print(usage_message)
