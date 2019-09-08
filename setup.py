import setuptools
#import os

REVISION = '0.1.5'
PROJECT_NAME = 'czpubtran'
PROJECT_AUTHORS = "Václav Chaloupka"
PROJECT_EMAILS = 'vasek.chaloupka@hotmail.com'
PROJECT_URL = "https://github.com/bruxy70/CzPubTran"
SHORT_DESCRIPTION = 'Calling CHAPS REST API to get information about public transit in CZ'

with open("README.md", "r") as fh:
    LONG = fh.read()

setuptools.setup(
    name=PROJECT_NAME.lower(),
    python_requires=">=3.6.0",
    version=REVISION,
    author=PROJECT_AUTHORS,
    author_email=PROJECT_EMAILS,
    packages=setuptools.find_packages(exclude=('test',)),
    install_requires=[
        'asyncio',
        'aiohttp',
        'async_timeout',
    ],
    url=PROJECT_URL,
    description=SHORT_DESCRIPTION,
    long_description=LONG,
    long_description_content_type="text/markdown",
    long_description_markdown_filename='README.md',  # uses setuptools-markdown
    license='MIT',
    classifiers=(
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ),
)
