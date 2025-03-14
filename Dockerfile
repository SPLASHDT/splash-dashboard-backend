FROM condaforge/miniforge3:latest


RUN mkdir /splash-dashboard-backend
COPY . /splash-dashboard-backend

RUN cd /splash-dashboard-backend && \
conda env create --file=env.yml -n backend
RUN conda init && conda clean -ya

ENV SPLASH_ENV=docker
ENTRYPOINT cd /splash-dashboard-backend && conda run -n backend --no-capture-output python main.py
EXPOSE 8080
