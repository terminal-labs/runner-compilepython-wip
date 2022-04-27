from setuptools import setup, find_packages

setup(
    name="noderunner",
    version='0.1',
    install_requires=[
        'requests',
        'flask',
        'Click',
        'cli-passthrough',
    ],
    packages=find_packages(),
    entry_points='''
        [console_scripts]
        noderunner=noderunner.runner:cli
    ''',
)
