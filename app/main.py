from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json

# Configuración inicial
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './app/data/images'
app.config['LABEL_FOLDER'] = './app/data/labels'
app.config['CLASSES_FILE'] = './app/data/classes.json'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['LABEL_FOLDER'], exist_ok=True)

# Asegurarse de que el archivo de clases exista
if not os.path.exists(app.config['CLASSES_FILE']):
    with open(app.config['CLASSES_FILE'], 'w') as f:
        json.dump([], f)

# Ruta principal
@app.route('/')
def index():
    # Cargar las imágenes dinámicamente desde el directorio
    images = os.listdir(app.config['UPLOAD_FOLDER'])
    with open(app.config['CLASSES_FILE'], 'r') as f:
        classes = json.load(f)
    return render_template('index.html', images=images, classes=classes)

# Ruta para añadir una nueva clase
@app.route('/add_class', methods=['POST'])
def add_class():
    data = request.get_json()
    new_class = data.get('class')

    if not new_class:
        return jsonify({'error': 'Class name is required'}), 400

    try:
        with open(app.config['CLASSES_FILE'], 'r') as f:
            classes = json.load(f)

        if new_class in classes:
            return jsonify({'message': 'Class already exists'})

        classes.append(new_class)
        with open(app.config['CLASSES_FILE'], 'w') as f:
            json.dump(classes, f)

        return jsonify({'message': 'Class added successfully', 'classes': classes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para obtener todas las clases
@app.route('/get_classes', methods=['GET'])
def get_classes():
    try:
        with open(app.config['CLASSES_FILE'], 'r') as f:
            classes = json.load(f)
        return jsonify({'classes': classes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Ruta para eliminar una clase
@app.route('/delete_class', methods=['POST'])
def delete_class():
    data = request.get_json()
    class_to_delete = data.get('class')

    if not class_to_delete:
        return jsonify({'error': 'Class name is required'}), 400

    try:
        with open(app.config['CLASSES_FILE'], 'r') as f:
            classes = json.load(f)

        if class_to_delete not in classes:
            return jsonify({'error': 'Class not found'}), 404

        classes.remove(class_to_delete)

        with open(app.config['CLASSES_FILE'], 'w') as f:
            json.dump(classes, f)

        return jsonify({'message': 'Class deleted successfully', 'classes': classes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Ruta para subir imágenes y devolver el nombre de la imagen cargada
@app.route('/upload_direct', methods=['POST'])
def upload_direct_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    return jsonify({'message': 'Image uploaded successfully', 'filename': file.filename})

# Ruta para eliminar una imagen
@app.route('/delete_image/<filename>', methods=['DELETE'])
def delete_image(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'message': 'Image deleted successfully'})
    return jsonify({'error': 'Image not found'}), 404

# Ruta para obtener una imagen
@app.route('/images/<filename>')
def get_image(filename):
    directory = os.path.abspath(app.config['UPLOAD_FOLDER'])  # Ruta absoluta
    print(f"Attempting to serve file from directory: {directory}")  # Depuración
    return send_from_directory(directory, filename)


# Ruta para guardar etiquetas
@app.route('/save_labels', methods=['POST'])
def save_labels():
    data = request.get_json()
    if not data or 'filename' not in data or 'labels' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    label_file = os.path.join(app.config['LABEL_FOLDER'], f"{data['filename']}.txt")
    try:
        with open(label_file, 'w') as f:
            for label in data['labels']:
                f.write(f"{label['class']} {label['x_center']} {label['y_center']} {label['width']} {label['height']}\n")
        return jsonify({'message': 'Labels saved successfully'})
    except Exception as e:
        return jsonify({'error': f"Failed to save labels: {str(e)}"}), 500

# Ruta para cargar etiquetas
@app.route('/load_labels/<filename>', methods=['GET'])
def load_labels(filename):
    label_file = os.path.join(app.config['LABEL_FOLDER'], f"{filename}.txt")
    if not os.path.exists(label_file):
        return jsonify({'error': 'Labels not found'}), 404

    labels = []
    try:
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                labels.append({
                    'class': parts[0],
                    'x_center': float(parts[1]),
                    'y_center': float(parts[2]),
                    'width': float(parts[3]),
                    'height': float(parts[4])
                })
        return jsonify({'labels': labels})
    except Exception as e:
        return jsonify({'error': f"Failed to load labels: {str(e)}"}), 500

if __name__ == '__main__':
    # Asegurarse de que las carpetas existan al inicio
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LABEL_FOLDER'], exist_ok=True)
    app.run(debug=True)