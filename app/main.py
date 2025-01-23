from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
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


@app.route('/save_labels', methods=['POST'])
def save_labels():
    try:
        app.logger.info("Processing /save_labels request...")

        # Obtener datos enviados por el frontend
        data = request.get_json()
        app.logger.info(f"Received data: {data}")

        # Extraer campos
        filename = data.get('filename')
        labels = data.get('labels')
        format = data.get('format')

        # Validar datos
        if not filename or not labels or not format:
            app.logger.error("Missing required fields.")
            return jsonify({'error': 'Missing required fields.'}), 400

        app.logger.info(f"Saving labels for {filename} in {format} format...")

        # Procesar según el formato seleccionado
        if format == 'yolo':
            save_labels_yolo(filename, labels)
        elif format == 'coco':
            save_labels_coco(filename, labels)
        elif format == 'pascal_voc':
            save_labels_pascal_voc(filename, labels)
        else:
            app.logger.error("Invalid format selected.")
            return jsonify({'error': 'Invalid format selected.'}), 400

        app.logger.info("Labels saved successfully.")
        return jsonify({'message': f'Labels saved successfully in {format} format'})
    except Exception as e:
        app.logger.error(f"Error while saving labels: {e}")
        return jsonify({'error': f"Failed to save labels: {str(e)}"}), 500


def save_labels_yolo(filename, labels):
    label_file = os.path.join(app.config['LABEL_FOLDER'], f"{filename}.txt")
    try:
        with open(label_file, 'w') as f:
            for label in labels:
                f.write(f"{label['class']} {label['x_center']} {label['y_center']} {label['width']} {label['height']}\n")
    except Exception as e:
        raise Exception(f"Error saving YOLO labels: {str(e)}")
    
def save_labels_coco(filename, labels):
    try:
        # Cargar las clases desde el archivo JSON
        with open(app.config['CLASSES_FILE'], 'r') as f:
            classes = json.load(f)

        # Validar que las clases en las etiquetas existan en el archivo de clases
        annotations = []
        for i, label in enumerate(labels):
            if label['class'] not in classes:
                raise ValueError(f"Class '{label['class']}' not found in classes file.")

            # Crear las anotaciones en formato COCO
            annotations.append({
                "id": i,  # ID único para la anotación
                "image_id": filename,  # ID de la imagen
                "category_id": classes.index(label['class']),  # Índice de la clase
                "bbox": [
                    max(0, label["x_center"] * 800 - (label["width"] * 800) / 2),  # xmin
                    max(0, label["y_center"] * 600 - (label["height"] * 600) / 2),  # ymin
                    label["width"] * 800,  # ancho
                    label["height"] * 600  # alto
                ],
                "area": label["width"] * 800 * label["height"] * 600,  # área del bounding box
                "iscrowd": 0  # No es una anotación agrupada
            })

        # Formato COCO completo
        coco_format = {
            "images": [
                {
                    "id": filename,  # ID único de la imagen
                    "file_name": filename,  # Nombre del archivo de la imagen
                    "width": 800,
                    "height": 600
                }
            ],
            "annotations": annotations,
            "categories": [
                {"id": i, "name": cls} for i, cls in enumerate(classes)
            ]
        }

        # Guardar el archivo en formato JSON
        label_path = os.path.join(app.config['LABEL_FOLDER'], f"{filename}_coco.json")
        with open(label_path, 'w') as f:
            json.dump(coco_format, f, indent=4)

    except Exception as e:
        raise Exception(f"Error saving COCO labels: {str(e)}")

def save_labels_pascal_voc(filename, labels):
    try:
        # Crear el nodo raíz del archivo XML
        root = Element("annotation")

        # Información básica de la imagen
        folder = SubElement(root, "folder")
        folder.text = "images"
        file_name = SubElement(root, "filename")
        file_name.text = filename
        size = SubElement(root, "size")
        width = SubElement(size, "width")
        width.text = "800"  # Ajustar según el tamaño de tus imágenes
        height = SubElement(size, "height")
        height.text = "600"
        depth = SubElement(size, "depth")
        depth.text = "3"

        # Añadir las etiquetas como objetos
        for label in labels:
            obj = SubElement(root, "object")
            name = SubElement(obj, "name")
            name.text = label['class']  # Nombre de la clase (texto)

            bndbox = SubElement(obj, "bndbox")
            xmin = SubElement(bndbox, "xmin")
            ymin = SubElement(bndbox, "ymin")
            xmax = SubElement(bndbox, "xmax")
            ymax = SubElement(bndbox, "ymax")

            # Calcular coordenadas absolutas a partir de x_center, y_center, width y height
            xmin.text = str(max(0, int((label["x_center"] - label["width"] / 2) * 800)))
            ymin.text = str(max(0, int((label["y_center"] - label["height"] / 2) * 600)))
            xmax.text = str(min(800, int((label["x_center"] + label["width"] / 2) * 800)))
            ymax.text = str(min(600, int((label["y_center"] + label["height"] / 2) * 600)))

        # Convertir a una cadena XML y guardar en un archivo
        label_path = os.path.join(app.config['LABEL_FOLDER'], f"{filename}_pascal_voc.xml")
        xml_str = parseString(tostring(root)).toprettyxml(indent="   ")
        with open(label_path, "w") as f:
            f.write(xml_str)

    except Exception as e:
        raise Exception(f"Error saving Pascal VOC labels: {str(e)}")

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

@app.route('/list_labels', methods=['GET'])
def list_labels():
    try:
        # Obtener la lista de archivos en la carpeta de etiquetas
        label_files = os.listdir(app.config['LABEL_FOLDER'])
        return jsonify({'labels': label_files})
    except Exception as e:
        return jsonify({'error': f"Failed to list labels: {str(e)}"}), 500



if __name__ == '__main__':
    # Asegurarse de que las carpetas existan al inicio
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LABEL_FOLDER'], exist_ok=True)
    app.run(debug=True)