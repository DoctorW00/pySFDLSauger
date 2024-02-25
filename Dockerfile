FROM python:3.12
WORKDIR /pySFDLSauger
COPY requirements.txt ./
COPY pySFDLSauger.py ./
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir /shared_host
CMD ["python", "./pySFDLSauger.py"]
