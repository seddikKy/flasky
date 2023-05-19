import code
import os
import sys
import unittest
import click
from app import create_app, db
from flask.cli import FlaskGroup
from flask_migrate import upgrade, Migrate
from app.models import Role, User
import coverage

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def create_app_wrapper():
    return app

cli = FlaskGroup(create_app=create_app_wrapper)
migrate = Migrate(app, db)

# def create_database():
#     with app.app_context():
#         db.create_all()
#         print("Database created successfully.")

# @cli.command("run")
# @click.option("--port", default=5000, help="Port to run the server on")
# def run(port):
#     app = create_app_wrapper()
#     app.run(port=port)

@cli.command("create_db")
def create_db():
    """Create the database tables."""
    db.create_all()
    print("Database created successfully.")


@cli.command("drop_db")
def drop_db():
    """Drop the database tables."""
    db.drop_all()

@cli.command("shell")
def shell():
    """Start a Python shell with the application context loaded."""
    ctx = app.make_shell_context()
    ctx.update({"app": app, "db": db}) 
    code.interact(local=ctx)


# @cli.command("test")
# def test():
#     """Run the unit tests for the application."""
#     import pytest
#     errno = pytest.main(["tests"])
#     sys.exit(errno)


COV = None

if os.environ.get('FLASK_COVERAGE'):
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()
@cli.command("test")
@click.option('--coverage', is_flag=True, help='Enable code coverage')
def test(coverage):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

@cli.command("routes")
def routes():
    """Display all routes defined in the application."""
    for rule in app.url_map.iter_rules():
        click.echo(rule)


@cli.command("db_upgrade")
def db_upgrade():
    """Upgrade the database to the latest migration."""
    with app.app_context():
        upgrade(directory="migrations")
        print("Database upgrade complete.")

@cli.command("createsuperuser")
@click.option("--email", prompt="Enter email", help="Email address")
@click.option("--username", prompt="Enter username", help="Username")
@click.option("--password", prompt="Enter password", hide_input=True, confirmation_prompt=True, help="Password")
def create_superuser(email, username, password):
    db.create_all()
    Role.insert_roles()
    role = Role.query.filter_by(name="Administrator").first()
    user = User(
        email=email,
        username=username,
        password=password,
        confirmed=1,
        role=role
    )
    db.session.add(user)
    db.session.commit()
    print('superuser created successfully')

@cli.command("profile")
@click.option('--length', default=25,
              help='Number of functions to include in the profiler report.')
@click.option('--profile-dir', default=None,
              help='Directory where profiler data files are saved.')
def profile(length, profile_dir):
    """Start the application under the code profiler."""
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                    profile_dir=profile_dir)
    if __name__ == '__main__':
        app.run(debug=False)
 

if __name__ == '__main__':
    # create_database()
    cli()
    