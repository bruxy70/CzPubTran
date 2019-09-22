python setup.py sdist bdist_wheel
python -m twine upload dist/*
rmdir /S /Q czpubtran.egg-info
rmdir /S /Q dist
rmdir /S /Q build