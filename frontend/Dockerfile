FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

ARG REACT_APP_API_URL=http://52.66.155.222:8000
ENV REACT_APP_API_URL=$REACT_APP_API_URL

RUN npm run build

RUN npm install -g serve

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]