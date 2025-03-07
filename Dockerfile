FROM condaforge/miniforge3:latest


RUN mkdir /splash-dashboard-backend
COPY . /splash-dashboard-backend

RUN cd /splash-dashboard-backend && \
conda env create --file=env.yml -n backend
RUN conda init

ENV SPLASH_ENV=docker
ENTRYPOINT conda run -n backend python /splash-dashboard-backend/main.py
EXPOSE 8080
