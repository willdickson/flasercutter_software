from setuptools import setup, find_packages

setup(
    name='flasercutter',
    version='0.1',
    description = 'Python pyqt app for controller the microscope/lasercutter',
    author='Will Dickson',
    author_email='wbd@caltech',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    packages=find_packages(exclude=[]),
    include_package_data=True,
    package_data = {'': ['*.ui']},
    entry_points = {
        'console_scripts' : ['flaser = flasercutter.app:app_main'],
        },
)
