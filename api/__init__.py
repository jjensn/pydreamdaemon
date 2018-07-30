from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route('/')
def get_index():
  return jsonify('index')


@app.route('/', methods=['POST'])
def post_index():
  return '', 204