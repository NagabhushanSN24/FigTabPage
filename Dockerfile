FROM python:3.9-alpine

RUN mkdir /app

WORKDIR /app

COPY ./ /app/

RUN pip install -r requirements.txt

ENTRYPOINT [ "python" ]

CMD [ "show.py" ]
