
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QThread, pyqtSignal
from sympy import Matrix, simplify, parse_expr, latex
from settings_ui import Ui_Cross
import sys
from PyQt5.QtWebEngineWidgets import QWebEngineView
import concurrent.futures



'''
    
    Background task for calculating the cross product

'''
class CalculateCross(QThread):
    success = pyqtSignal(str)
    fail = pyqtSignal(str)
    active = pyqtSignal()
    done = pyqtSignal()
    
    def __init__(self, u, v, action):
        super().__init__()
        self.u = u
        self.v = v
        self.action = action

    def run(self):
        self.active.emit()
        try:
            if self.action == "cross":
                result = self.calc_cross()
               
            elif self.action in {"u", "v"}:
                result = self.update_vector()

            self.success.emit(str(result))
        
        except Exception:
            self.fail.emit("Bad input")
        finally:    
            self.done.emit()

    """
        Helper method to ensure update_vector finishes within the specified amount of time.
        If it doesn't quit and return a timeout message
        
        Reruena the result of update_vector if it completes within the timeout, 
        otherwise raises TimeoutError.
    """
    def execute_with_timeout(self, func, *args, timeout=5):
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(func, *args)
            return future.result(timeout=timeout)
    
   
    """    
        Generate a LaTeX string representation of the matrix
    """
      
    def update_vector(self):
        try:
            # Attempt to generate LaTeX with a timeout
            result = self.execute_with_timeout(lambda: f"${latex(Matrix(self.u))}$")
        except concurrent.futures.TimeoutError:
            result = "Timeout Error"
        except Exception:
            result = "Bad Input"
      
        return result
  

    '''
        Compute the cross product
    '''
    def calc_cross(self):
        try:
            # Attempt to generate LaTeX with a timeout
            cross = self.execute_with_timeout(lambda: Matrix(self.u).cross(Matrix(self.v)), timeout=1)
            result = f"${latex(cross)}$"
        except concurrent.futures.TimeoutError:
            result = "Timeout Error"
        except Exception:
            result = "Bad Input"
        
        return result
        
 
"""
    Class for managing the cross product GUI
"""
class CrossProductCalculator(QMainWindow, Ui_Cross):
    def __init__(self):
        QMainWindow.__init__(self)
        Ui_Cross.__init__(self)
        self.setupUi(self)

        self.num_cross_threads = 0
        self.num_u_threads = 0
        self.num_v_threads = 0
        self.threads = []

        # add web views to display latex
        self.result_webView = QWebEngineView(self)
        layout = self.result_widget.layout()
        layout.addWidget(self.result_webView)

        self.u_webView = QWebEngineView(self)
        layout = self.u_widget.layout()
        layout.addWidget(self.u_webView)

        self.v_webView = QWebEngineView(self)
        layout = self.v_widget.layout()
        layout.addWidget(self.v_webView)

        # populate vector with default values
        self.u1_lineEdit.setText("sqrt(I**2 *4)")
        self.u2_lineEdit.setText("sin(pi / 4) + cos(pi / 4)")
        self.u3_lineEdit.setText("log(16,2)")
        self.v1_lineEdit.setText("diff(cos(x),x)")
        self.v2_lineEdit.setText("limit(sin(x)/x, x, 0)")
        self.v3_lineEdit.setText("integrate(exp(-x**2 - y**2), (x, -oo, oo), (y, -oo, oo))")


        # Connect buttons
        self.cross_pushButton.clicked.connect(self.compute_cross_product)
        self.u1_lineEdit.editingFinished.connect(lambda: self.update_vector("u"))
        self.u2_lineEdit.editingFinished.connect(lambda: self.update_vector("u"))
        self.u3_lineEdit.editingFinished.connect(lambda: self.update_vector("u"))
        self.v1_lineEdit.editingFinished.connect(lambda: self.update_vector("v"))
        self.v2_lineEdit.editingFinished.connect(lambda: self.update_vector("v"))
        self.v3_lineEdit.editingFinished.connect(lambda: self.update_vector("v"))

        # set tab order
        self.setTabOrder(self.u1_lineEdit, self.u2_lineEdit)
        self.setTabOrder(self.u2_lineEdit, self.u3_lineEdit)
        self.setTabOrder(self.u3_lineEdit, self.v1_lineEdit)
        self.setTabOrder(self.v1_lineEdit, self.v2_lineEdit)
        self.setTabOrder(self.v2_lineEdit, self.v3_lineEdit)
        self.setTabOrder(self.v3_lineEdit, self.cross_pushButton)

        # Initial LaTeX rendering
        self.update_vector("u")
        self.update_vector("v")

    """
        Simplifies the specified vector, and displays the result as 
        rendered latex
    """
    def update_vector(self, name):
        
        if name == "u":
            vect = [self.u1_lineEdit.text(), self.u2_lineEdit.text(), self.u3_lineEdit.text()]
            web_view = self.u_webView
            
        elif name == "v":
            vect = [self.v1_lineEdit.text(), self.v2_lineEdit.text(), self.v3_lineEdit.text()]
            web_view = self.v_webView
            

        thread = CalculateCross(u=vect, v=[], action="u" if name == "u" else "v")
        thread.success.connect(lambda latex_code: self.writeLatex(latex_code, web_view))
        thread.fail.connect(lambda error_code: self.writeLatex(error_code, web_view))
        thread.active.connect(lambda: self.startThread(name))  
        thread.done.connect(lambda: self.removeThread(thread, name)) 
        self.threads.append(thread)
        thread.start()


    '''
        Computes the cross product of u and v, and displays the 
        result as rendered latex
    '''
    def compute_cross_product(self):
        # Read vector components from individual line edits
        u_vector = [
            self.u1_lineEdit.text(),
            self.u2_lineEdit.text(),
            self.u3_lineEdit.text()
        ]

        v_vector = [
            self.v1_lineEdit.text(),
            self.v2_lineEdit.text(),
            self.v3_lineEdit.text()
        ]

        thread = CalculateCross(u=u_vector, v=v_vector, action="cross")
        thread.success.connect(lambda latex_code: self.writeLatex(latex_code, self.result_webView))
        thread.fail.connect(lambda error_code: self.writeLatex(error_code, self.result_webView))
        thread.active.connect(lambda: self.startThread("cross")) 
        thread.done.connect(lambda:self.removeThread(thread, "cross"))  
        self.threads.append(thread)
        thread.start()



    """
        Render LaTeX using MathJax and display it in the QTextBrowser.
    """
    def writeLatex(self, latex_code, web_view):
        
        # MathJax HTML content
        mathjax_html = f"""
        <html>
            <head>
                <script>
                    MathJax = {{
                        tex: {{
                            inlineMath: [['$', '$'], ['\\\(', '\\\)']],
                        }},
                        svg: {{
                            fontCache: 'global'
                        }}

                    }};
                </script>
                <script type='text/javascript' id='MathJax-script'
                async src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js'></script>
            </head>
            <body>
                {latex_code}
            </body>
        </html>
        """

        # Load the HTML in the QWebEngineView
        web_view.setHtml(mathjax_html)


    '''
        Lock buttons if threads running
    '''
    def startThread(self, name=None):
        if name == "u":
            self.num_u_threads +=1
            self.u1_lineEdit.setReadOnly(True)
            self.u2_lineEdit.setReadOnly(True)
            self.u3_lineEdit.setReadOnly(True)
        if name == "v":
            self.num_v_threads +=1
            self.v1_lineEdit.setReadOnly(True)
            self.v2_lineEdit.setReadOnly(True)
            self.v3_lineEdit.setReadOnly(True)
        if name == "cross":
            self.num_cross_threads +=1
            self.u1_lineEdit.setReadOnly(True)
            self.u2_lineEdit.setReadOnly(True)
            self.u3_lineEdit.setReadOnly(True)
            self.v1_lineEdit.setReadOnly(True)
            self.v2_lineEdit.setReadOnly(True)
            self.v3_lineEdit.setReadOnly(True)
            self.cross_pushButton.setEnabled(False)

        print(f"Added {name}")
        print(f"cross { self.num_cross_threads}")
        print(f"u { self.num_u_threads}")
        print(f"v { self.num_v_threads}")
           
    
    '''
        Unlock buttons if no threads running
    '''
    def removeThread(self, thread, name=None):
        self.threads.remove(thread)
            
        if name == "cross":
            self.num_cross_threads -= 1
    
        if name == "u":
            self.num_u_threads -= 1
        
        if name == "v":
            self.num_v_threads -= 1
           

        if self.num_cross_threads == 0: 
                self.cross_pushButton.setEnabled(True)

        if self.num_u_threads == 0 and self.num_cross_threads == 0:  
            self.u1_lineEdit.setReadOnly(False)
            self.u2_lineEdit.setReadOnly(False)
            self.u3_lineEdit.setReadOnly(False)

        if self.num_v_threads == 0 and self.num_cross_threads == 0:  
                self.v1_lineEdit.setReadOnly(False)
                self.v2_lineEdit.setReadOnly(False)
                self.v3_lineEdit.setReadOnly(False)

        print(f"Removed {name}")
        print(f"cross { self.num_cross_threads}")
        print(f"u { self.num_u_threads}")
        print(f"v { self.num_v_threads}")

    '''
        Stop all threads before closing application
    '''
    def closeEvent(self, event):
        for thread in self.threads:
            thread.quit()
            thread.wait()
        event.accept()



'''
    Parses a component string into a symbolic expression.
'''
def parse_component(component_str, eval=True):
    return parse_expr(component_str.strip(), evaluate=eval)
        

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_window = CrossProductCalculator()
    main_window.show()
    sys.exit(app.exec_())