import { Injectable } from '@angular/core';
import { RequestHandler } from 'app/classes/RequestHandler';
import { Project } from 'app/classes/project';

@Injectable({
  providedIn: 'root'
})
export class StatsDataService {
  /* Request handler to deal with requests */
  private requestHandler: RequestHandler;
  /* Session token for authentication */
  private sessionToken: string | null;

  constructor() {
    this.sessionToken = sessionStorage.getItem('ses_token');
    this.requestHandler = new RequestHandler(this.sessionToken);
  }

  /**
     * Function does call to backend to retrieve data from a single project
     * 
     * @params p_id: number
     * @pre p_id => 1
     * @throws Error if p_id < 1
     * @returns Promise<Record<string, any>>
     */
  async getProject(p_id: number): Promise<Record<string, any>> {
    // Check if the p_id is larger than 1
    if (p_id < 1) throw new Error("p_id cannot be less than 1");

    // Make a request to the backend to get project data
    let response = await this.requestHandler.get('/project/singleProject', { 'p_id': p_id }, true)
    // Initialize a new project with all values
    let projectJson = response["project"];

    // Create the project with constructor
    let projectNew = new Project(
      // Project id
      projectJson["id"],
      // Project name
      projectJson["name"],
      // Project description
      projectJson["description"]
    )

    // Set other variables
    // Number of artifacts in the project
    projectNew.setNumberOfArtifacts(response["projectNrArtifacts"]);
    // Number of completely labelled artifacts in the project
    projectNew.setNumberOfCLArtifacts(response["projectNrCLArtifacts"]);
    // List of users in the project
    projectNew.setUsers(response["projectUsers"]);

    // Return project data
    return {
      'project_data': projectNew,
      // Return number of conflicts in project
      'conflicts': response["conflicts"],
      // Return number of labels in project
      'labels': response["labels"]
    }
  }

  /**
     * Function does call to backend to retrieve 
     * 
     * @params p_id: number
     * @pre p_id => 1
     * @throws Error if p_id < 1
     */
  async getUserStats(p_id: number): Promise<any> {
    // Check if the p_id is larger than 1
    if (p_id < 1) throw new Error("p_id cannot be less than 1");

    // Make a request to the backend to get user statistics
    return await this.requestHandler.get('/project/projectStats', { 'p_id': p_id }, true)
  }

  /**
   * Downloads the labellings of a project as a file.
   * Project admins get the labellings of all users, other members only their own.
   *
   * @params p_id: number
   * @params format: 'csv' (for spreadsheets) or 'json' (exact values, for scripts)
   * @pre p_id => 1
   * @throws Error if p_id < 1
   */
  async exportLabellings(p_id: number, format: 'csv' | 'json'): Promise<void> {
    if (p_id < 1) throw new Error("p_id cannot be less than 1");

    const file = await this.requestHandler.getFile(
      '/export/labellings', { 'p_id': p_id, 'format': format }, true);

    // Let the browser save the file
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lama_project_${p_id}_labellings.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}
