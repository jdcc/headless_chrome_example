from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
        name='headlesschrome',
        version='0.1.0',
        description='An interface to headless Chrome',
        packages=find_packages(exclude=['tests']),
        install_requires=['requests', 'websockets'],
        )
